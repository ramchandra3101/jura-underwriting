from __future__ import annotations

import re
from typing import Any

from jura.guards import VALID_STATES, GuardResult

_REQUIRED_FIELDS = {
    "insured_name", "state", "zip_code", "sic_code",
    "tiv", "credit_score_used", "new_business",
}

# Adversarial patterns that indicate prompt injection attempts in source documents
_INJECTION_PATTERNS = [
    r"ignore\s+(previous|prior|all)\s+instructions",
    r"disregard\s+(the\s+)?(above|previous|prior)",
    r"forget\s+(your|all|the)\s+(instructions|rules|context)",
    r"you\s+are\s+now\s+a",
    r"new\s+instructions\s*:",
    r"override\s+(the\s+)?(field|value|state|tiv)",
    r"set\s+(state|tiv|zip|sic)\s+to",
    r"<\s*/?(?:system|prompt|instruction)\s*>",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


# ---------------------------------------------------------------------------
# Guard 4 — Prompt injection scan (DOCX text before regex field extraction)
# ---------------------------------------------------------------------------

def scan_for_injection(text: str) -> GuardResult:
    hits: list[str] = []
    for pattern in _COMPILED:
        m = pattern.search(text)
        if m:
            hits.append(f"Suspicious pattern in document: {m.group()!r}")
    return GuardResult(passed=len(hits) == 0, errors=hits)


# ---------------------------------------------------------------------------
# Guard 1 — Extraction output validation (after Gemini returns)
# ---------------------------------------------------------------------------

def validate_extraction(fields: dict[str, Any]) -> GuardResult:
    errors: list[str] = []
    warnings: list[str] = []

    # Presence — missing fields are blocking; human must fill before confirming
    missing = [f for f in _REQUIRED_FIELDS if fields.get(f) is None]
    for f in missing:
        errors.append(f"{f!r} could not be extracted — fill in before confirming")
    if missing:
        return GuardResult(passed=False, errors=errors, warnings=warnings)

    # State
    state = fields.get("state", "")
    if not isinstance(state, str) or state.upper() not in VALID_STATES:
        errors.append(f"state {state!r} is not a valid US state code")

    # ZIP
    zip_code = str(fields.get("zip_code", ""))
    if not re.fullmatch(r"\d{5}", zip_code):
        errors.append(f"zip_code {zip_code!r} must be exactly 5 digits")

    # SIC
    sic = str(fields.get("sic_code", ""))
    if not re.fullmatch(r"\d{4}", sic):
        errors.append(f"sic_code {sic!r} must be exactly 4 digits")

    # TIV
    try:
        tiv = float(fields.get("tiv") or 0)
    except (TypeError, ValueError):
        tiv = 0.0
        errors.append("tiv must be a number")
    if tiv <= 0:
        errors.append("tiv must be greater than 0")
    elif tiv > 500_000_000:
        warnings.append(f"tiv ${tiv:,.0f} is unusually high — verify before confirming")

    # Boolean fields
    for field in ("credit_score_used", "new_business"):
        val = fields.get(field)
        if not isinstance(val, bool):
            warnings.append(f"{field!r} defaulted to false — verify if correct")

    # Guard 4b — post-extraction anomaly check
    name = str(fields.get("insured_name", ""))
    if len(name) > 200:
        errors.append("insured_name is suspiciously long — possible injection in extracted field")
    for pattern in _COMPILED:
        for key, val in fields.items():
            if isinstance(val, str) and pattern.search(val):
                errors.append(
                    f"Suspicious content in extracted field {key!r}: {val[:80]!r}"
                )

    return GuardResult(passed=len(errors) == 0, errors=errors, warnings=warnings)
