from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from jura.audit import JurisdictionAuditLogger
from jura.checker import generate_es_mock_declinations, run_jurisdiction_check
from jura.db import SubmissionDB
from jura.models import (
    ESResult,
    JurisdictionBlock,
    JurisdictionResult,
    MultiStateConflict,
    SubmissionEvent,
)
from jura.pipeline import forward_to_next_agent


class JurisdictionRouter:
    def __init__(
        self,
        db: SubmissionDB,
        audit: JurisdictionAuditLogger,
        notices: Any,          # module ref (write_* functions imported directly)
        llm_client: Any,
        hitl_mode: str = "terminal",
    ) -> None:
        self.db = db
        self.audit = audit
        self.notices = notices
        self.llm_client = llm_client
        self.hitl_mode = hitl_mode

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def route(self, event: SubmissionEvent) -> dict:
        self.db.upsert(event.model_dump())

        try:
            result = run_jurisdiction_check(event)
        except JurisdictionBlock as exc:
            # B5 — audit gap fix: record every block, even when the checker
            # raises before a JurisdictionResult exists.
            self.audit.log_blocked(
                submission_id=event.submission_id,
                insured_name=event.insured_name,
                blocked_reason=exc.reason,
                statutory_ref=exc.statutory_ref,
            )
            return {
                "outcome": "blocked",
                "submission_id": event.submission_id,
                "reason": exc.reason,
                "statutory_ref": exc.statutory_ref,
            }
        except MultiStateConflict as exc:
            return {
                "outcome": "multi_state_conflict",
                "submission_id": event.submission_id,
                "states": exc.states,
                "conflicts": exc.conflicting_rules,
                "summary": exc.conflict_summary,
            }

        self.audit.log_jurisdiction(result, insured_name=event.insured_name)

        forward_meta = forward_to_next_agent(result)
        self.audit.log_forwarded(
            submission_id=result.submission_id,
            target=result.routed_to,
            forward_meta=forward_meta,
        )

        return {
            "outcome": result.routed_to,
            "submission_id": result.submission_id,
            "market": result.market,
            "routed_to": result.routed_to,
            "forward": forward_meta,
        }
