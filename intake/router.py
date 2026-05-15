from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from intake import store
from intake.converter import docx_to_text
from intake.guards import scan_for_injection, validate_extraction
from intake.ocr_extractor import extract_from_docx_text, extract_from_pdf_acroform
from jura.models import SubmissionEvent

router = APIRouter(prefix="/intake", tags=["intake"])


class ConfirmRequest(BaseModel):
    submission_id: str | None = None
    insured_name: str
    state: str
    zip_code: str
    sic_code: str
    tiv: float
    credit_score_used: bool
    new_business: bool


@router.post("/upload")
async def upload_documents(files: list[UploadFile] = File(...)):
    """Accept one or more PDF/DOCX files. Returns one draft per file for human review."""

    async def process(file: UploadFile) -> dict[str, Any]:
        content = await file.read()
        fname = file.filename or "unknown"
        try:
            if fname.lower().endswith(".docx"):
                text = docx_to_text(content)
                # Guard 4: scan for prompt injection before field extraction
                injection = scan_for_injection(text)
                if not injection.passed:
                    return {"error": f"Injection detected in {fname!r}: {'; '.join(injection.errors)}", "source_file": fname}
                fields = extract_from_docx_text(text)
            elif fname.lower().endswith(".pdf"):
                fields = extract_from_pdf_acroform(content, fname)
            else:
                return {"error": f"Unsupported file type: {fname}", "source_file": fname}
        except Exception as exc:
            return {"error": str(exc), "source_file": fname}

        # Guard 1: validate extraction output
        guard = validate_extraction(fields)

        draft_id = str(uuid.uuid4())
        draft: dict[str, Any] = {
            "draft_id": draft_id,
            "source_file": fname,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "fields": fields,
            "status": "needs_review" if not guard.passed else "pending",
            "validation": {
                "passed": guard.passed,
                "errors": guard.errors,
                "warnings": guard.warnings,
            },
        }
        store.upsert(draft_id, draft)
        return draft

    results = await asyncio.gather(*[process(f) for f in files])
    return {"drafts": list(results), "count": len(results)}


@router.get("/drafts")
def list_drafts():
    return {"drafts": store.list_all()}


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: str):
    draft = store.get(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=f"Draft {draft_id!r} not found")
    return draft


@router.patch("/drafts/{draft_id}")
def patch_draft(draft_id: str, fields: dict[str, Any]):
    """Partially update extracted fields (human edits before confirmation).
    Re-runs Guard 1 after patch so the review screen reflects current validity."""
    updated = store.patch_fields(draft_id, fields)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Draft {draft_id!r} not found")

    guard = validate_extraction(updated["fields"])
    store.patch_validation(
        draft_id,
        status="needs_review" if not guard.passed else "pending",
        validation={"passed": guard.passed, "errors": guard.errors, "warnings": guard.warnings},
    )
    return store.get(draft_id)


@router.post("/confirm/{draft_id}")
async def confirm_draft(draft_id: str, body: ConfirmRequest, request: Request):
    """Human confirms (and optionally overrides) extracted fields. Routes to /jurisdiction.
    Guard 2 runs inside jurisdiction_router.route()."""
    draft = store.get(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=f"Draft {draft_id!r} not found")
    if draft["status"] == "confirmed":
        raise HTTPException(status_code=409, detail="Draft already confirmed")

    submission_id = body.submission_id or f"SUB-{uuid.uuid4().hex[:8].upper()}"
    event = SubmissionEvent(
        submission_id=submission_id,
        insured_name=body.insured_name,
        state=body.state,
        zip_code=body.zip_code,
        sic_code=body.sic_code,
        tiv=body.tiv,
        credit_score_used=body.credit_score_used,
        new_business=body.new_business,
    )

    jurisdiction_router = request.app.state.router
    result = await jurisdiction_router.route(event)

    # Guard 2 rejection surfaces as outcome="guard_rejected" from the router
    if isinstance(result, dict) and result.get("outcome") == "guard_rejected":
        raise HTTPException(
            status_code=422,
            detail={"message": "Submission failed validation", **result},
        )

    store.mark_confirmed(draft_id)
    return {
        "draft_id": draft_id,
        "submission_id": submission_id,
        "jurisdiction": result,
    }


@router.delete("/drafts/{draft_id}")
def delete_draft(draft_id: str):
    if not store.delete(draft_id):
        raise HTTPException(status_code=404, detail=f"Draft {draft_id!r} not found")
    return {"deleted": draft_id}
