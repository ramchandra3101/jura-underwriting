from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

from pydantic import BaseModel

from jura.models import JurisdictionResult, SubmissionEvent

if TYPE_CHECKING:
    from jura.db import SubmissionDB

_HIGH_VALUE_THRESHOLD = float(os.getenv("HIGH_VALUE_TIV", "5000000"))

VALID_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


class GuardResult(BaseModel):
    passed: bool
    errors: list[str] = []
    warnings: list[str] = []


# ---------------------------------------------------------------------------
# Guard 2 — Submission input validation
# ---------------------------------------------------------------------------

def validate_submission(event: SubmissionEvent, db: "SubmissionDB") -> GuardResult:
    errors: list[str] = []
    warnings: list[str] = []

    if db.get(event.submission_id) is not None:
        warnings.append(
            f"submission_id {event.submission_id!r} already exists — possible duplicate resubmission"
        )

    if event.state not in VALID_STATES:
        errors.append(f"state {event.state!r} is not a valid US state code")

    if not re.fullmatch(r"\d{5}", event.zip_code):
        errors.append(f"zip_code {event.zip_code!r} must be exactly 5 digits")

    if not re.fullmatch(r"\d{4}", event.sic_code):
        errors.append(f"sic_code {event.sic_code!r} must be exactly 4 digits")

    if event.tiv <= 0:
        errors.append(f"tiv must be greater than 0 (got {event.tiv})")
    elif event.tiv > 500_000_000:
        warnings.append(f"tiv ${event.tiv:,.0f} is unusually high — verify before routing")

    return GuardResult(passed=len(errors) == 0, errors=errors, warnings=warnings)


# ---------------------------------------------------------------------------
# Guard 3 — High-value escalation
# ---------------------------------------------------------------------------

def apply_high_value_guard(result: JurisdictionResult, tiv: float) -> JurisdictionResult:
    if result.routed_to != "aria" or tiv < _HIGH_VALUE_THRESHOLD:
        return result
    return result.model_copy(update={
        "routed_to": "compliance_queue",
        "rationale": (
            f"{result.rationale} "
            f"[Guard] High-value escalation: TIV ${tiv:,.0f} exceeds "
            f"${_HIGH_VALUE_THRESHOLD:,.0f} threshold — routed to compliance queue for human review."
        ),
    })
