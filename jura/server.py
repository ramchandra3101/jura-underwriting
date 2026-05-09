from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from rich.console import Console

from compliance.review import router as compliance_router
from jura.audit import JurisdictionAuditLogger
from jura.checker import ADMITTED_STATES, run_jurisdiction_check
from jura.db import SubmissionDB, _SEED
from jura.llm import get_client, get_provider, get_provider_config, llm_status
from jura.models import JurisdictionBlock, JurisdictionResult, SubmissionEvent
from jura.router import JurisdictionRouter
from jura.views import router as views_router

_ROOT = Path(__file__).parent.parent

console = Console()

_VERSION = "0.1.0"

# ---------------------------------------------------------------------------
# In-memory session state
# ---------------------------------------------------------------------------

SESSION_RESULTS: dict[str, JurisdictionResult] = {}


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()

    db = SubmissionDB()
    db.seed()
    audit = JurisdictionAuditLogger()
    llm_client = get_client()
    hitl_mode = os.environ.get("HITL_MODE", "terminal")

    import jura.notices as notices_module
    router = JurisdictionRouter(
        db=db,
        audit=audit,
        notices=notices_module,
        llm_client=llm_client,
        hitl_mode=hitl_mode,
    )

    app.state.db = db
    app.state.audit = audit
    app.state.router = router

    provider = get_provider()
    pcfg = get_provider_config()
    aria_endpoint = os.environ.get("ARIA_ENDPOINT", "http://localhost:8001/score")

    console.print()
    console.print("[bold cyan]Jura — Jurisdiction & Regulatory Authority agent[/bold cyan]")
    console.print(f"  Provider: [green]{provider}[/green] · Model: [green]{pcfg['model']}[/green]")
    console.print(f"  Aria endpoint: [dim]{aria_endpoint}[/dim]")
    console.print(f"  HITL mode: [yellow]{hitl_mode}[/yellow]")
    console.print(f"  Port: [dim]8003[/dim]")
    console.print()

    yield
    # shutdown — nothing to tear down


app = FastAPI(title="Jura", version=_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(views_router)
app.include_router(compliance_router)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_row_to_event(row: dict) -> SubmissionEvent:
    return SubmissionEvent(**row)


def _evaluate(submission: SubmissionEvent) -> JurisdictionResult:
    """Run jurisdiction check, audit it, forward to next agent, store result."""
    audit: JurisdictionAuditLogger = app.state.audit
    try:
        result = run_jurisdiction_check(submission)
    except JurisdictionBlock as exc:
        result = JurisdictionResult(
            submission_id=submission.submission_id,
            insured_name=submission.insured_name,
            market="blocked",
            doi_flags=[],
            rationale=f"Submission blocked. {exc.statutory_ref}. Statutory hold issued.",
            routed_to="blocked",
            blocked_reason=exc.statutory_ref,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    audit.log_jurisdiction(result, insured_name=submission.insured_name)

    from jura.pipeline import forward_to_next_agent
    forward_meta = forward_to_next_agent(result)
    audit.log_forwarded(
        submission_id=result.submission_id,
        target=result.routed_to,
        forward_meta=forward_meta,
    )

    # If a live Aria call was attempted, append the second-leg audit entry.
    aria = forward_meta.get("aria")
    if isinstance(aria, dict):
        if "status_code" in aria:
            audit.log_response_received(
                submission_id=result.submission_id,
                target=result.routed_to,
                status_code=aria["status_code"],
                response=aria.get("response"),
            )
        elif "error" in aria:
            audit.log_unreachable(
                submission_id=result.submission_id,
                target=result.routed_to,
                url=aria.get("url", ""),
                error=aria["error"],
                error_type=aria.get("error_type", "Exception"),
            )

    SESSION_RESULTS[result.submission_id] = result
    return result


# ---------------------------------------------------------------------------
# Endpoints (existing)
# ---------------------------------------------------------------------------

@app.post("/jurisdiction")
async def post_jurisdiction(event: SubmissionEvent):
    router: JurisdictionRouter = app.state.router
    return await router.route(event)


@app.get("/submissions")
def get_submissions(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
):
    db: SubmissionDB = app.state.db
    return db.list_submissions(status=status, limit=limit)


@app.get("/submissions/{submission_id}")
def get_submission(submission_id: str):
    db: SubmissionDB = app.state.db
    row = db.get_submission(submission_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Submission {submission_id!r} not found")
    return row


@app.get("/health")
def get_health():
    return {
        "status": "ok",
        "version": _VERSION,
        "hitl_mode": os.environ.get("HITL_MODE", "terminal"),
        "llm": llm_status(),
        "aria_endpoint": os.environ.get("ARIA_ENDPOINT", "http://localhost:8001/score"),
    }


@app.post("/test/submit/{n}")
async def test_submit(n: int):
    if not (0 <= n <= 4):
        raise HTTPException(status_code=400, detail="n must be 0–4")
    router: JurisdictionRouter = app.state.router
    row = _SEED[n]
    event = _seed_row_to_event(row)
    return await router.route(event)


# ---------------------------------------------------------------------------
# Endpoints (new — Phase A4)
# ---------------------------------------------------------------------------

@app.post("/evaluate", response_model=JurisdictionResult)
async def post_evaluate(submission: SubmissionEvent) -> JurisdictionResult:
    return _evaluate(submission)


@app.post("/evaluate/{submission_id}", response_model=JurisdictionResult)
async def post_evaluate_by_id(submission_id: str) -> JurisdictionResult:
    db: SubmissionDB = app.state.db
    row = db.get(submission_id)
    if row is None:
        # Fall back to the seed list so the route works pre-seed
        for s in _SEED:
            if s["submission_id"] == submission_id:
                row = s
                break
    if row is None:
        raise HTTPException(status_code=404, detail=f"Submission {submission_id!r} not found")
    submission = _seed_row_to_event(row)
    return _evaluate(submission)


@app.get("/results", response_model=list[JurisdictionResult])
def get_results() -> list[JurisdictionResult]:
    return list(SESSION_RESULTS.values())


@app.get("/results/{submission_id}", response_model=JurisdictionResult)
def get_result(submission_id: str) -> JurisdictionResult:
    result = SESSION_RESULTS.get(submission_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Result {submission_id!r} not found")
    return result


@app.get("/audit/{submission_id}")
def get_audit(submission_id: str):
    audit: JurisdictionAuditLogger = app.state.audit
    return audit.events_for(submission_id)


@app.get("/demo/run-all", response_model=list[JurisdictionResult])
def demo_run_all() -> list[JurisdictionResult]:
    db: SubmissionDB = app.state.db
    SESSION_RESULTS.clear()
    results: list[JurisdictionResult] = []
    for row in _SEED:
        submission = _seed_row_to_event(row)
        db.upsert(row)
        results.append(_evaluate(submission))
    return results


@app.get("/demo/reset")
def demo_reset():
    db: SubmissionDB = app.state.db
    audit: JurisdictionAuditLogger = app.state.audit
    SESSION_RESULTS.clear()
    audit.clear()
    db.seed()
    return {"reset": True, "submissions_seeded": len(_SEED)}
