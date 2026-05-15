"""Rule-based ACORD field extractor — PDF (AcroForm) and DOCX (regex).

PDF path:  pypdf AcroForm field access by standard ACORD field names.
DOCX path: regex pattern matching on text extracted by intake.converter.

No LLM, no external API, no OCR engine required for either path.
Falls back to None for missing string fields and False for missing booleans.
"""
from __future__ import annotations

import io
import re
from typing import Any

import pypdf


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _str(val: Any) -> str:
    if val is None:
        return ""
    s = str(val).strip()
    if s.startswith("/") and s not in ("/On", "/1"):
        return ""
    return s


def _is_on(val: Any) -> bool:
    return str(val).strip() in ("/On", "/1", "On", "1", "Yes", "YES", "true", "True")


def _dollars(s: str) -> float:
    cleaned = re.sub(r"[^\d.]", "", s)
    return float(cleaned) if cleaned else 0.0


def _state_from_address(address: str) -> str | None:
    m = re.search(r",\s*([A-Z]{2})\s+\d{5}", address)
    return m.group(1) if m else None


def _zip_from_address(address: str) -> str | None:
    m = re.search(r"\b(\d{5})\b", address)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def extract_from_pdf_acroform(pdf_bytes: bytes, filename: str) -> dict[str, Any]:
    """Extract the 7 ACORD submission fields from a filled PDF AcroForm."""
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    fields: dict[str, Any] = reader.get_fields() or {}

    def get(key: str) -> str:
        field = fields.get(key)
        return _str(field.get("/V", "")) if field else ""

    def is_on(key: str) -> bool:
        field = fields.get(key)
        return _is_on(field.get("/V", "")) if field else False

    # --- insured_name ---
    insured_name: str | None = get("ACORD_Policy_Insured1_Name") or None

    # --- state ---
    state: str | None = get("ACORD_Location1_State") or None
    if not state:
        addr = get("ACORD_Policy_Insured1_MailingAddress")
        state = _state_from_address(addr) if addr else None

    # --- zip_code ---
    zip_code: str | None = get("ACORD_Location1_ZIP") or None
    if not zip_code:
        addr = get("ACORD_Policy_Insured1_MailingAddress")
        zip_code = _zip_from_address(addr) if addr else None

    # --- sic_code ---
    sic_code: str | None = get("ACORD_Policy_Insured1_SIC") or None

    # --- tiv ---
    # Sum every CommercialProperty LimitAmount field (BPP, Building, BI, etc.)
    tiv = 0.0
    for name, field in fields.items():
        if "CommercialProperty" in name and "LimitAmount" in name:
            raw = _str(field.get("/V", ""))
            if raw and raw != "$":
                try:
                    tiv += _dollars(raw)
                except ValueError:
                    pass
    # Fallback: try BusinessIncome / Building limit fields
    if tiv == 0.0:
        for name, field in fields.items():
            if ("BusinessIncome" in name or "BuildingLimit" in name) and "LimitAmount" in name:
                raw = _str(field.get("/V", ""))
                if raw and raw != "$":
                    try:
                        tiv += _dollars(raw)
                    except ValueError:
                        pass

    # --- credit_score_used ---
    # ACORD 125 has no standard credit-score-used checkbox.
    # Scan for any non-standard credit indicator fields; default False.
    credit_score_used = False
    for name, field in fields.items():
        nl = name.lower()
        if "credit" in nl and any(k in nl for k in ("used", "applied", "indicator", "score")):
            if _is_on(field.get("/V", "")):
                credit_score_used = True
                break

    # --- new_business ---
    # ACORD_Transaction_Quote = '/On' → new submission (quote = new business)
    # ACORD_Transaction_Renew  = '/On' → renewal
    new_business = False
    if is_on("ACORD_Transaction_Quote") or is_on("ACORD_Transaction_NewBusiness"):
        new_business = True
    elif is_on("ACORD_Transaction_Renew") or is_on("ACORD_Transaction_Renewal"):
        new_business = False

    return {
        "insured_name": insured_name,
        "state": state.upper() if state else None,
        "zip_code": zip_code,
        "sic_code": sic_code,
        "tiv": tiv if tiv > 0 else 0.0,
        "credit_score_used": credit_score_used,
        "new_business": new_business,
    }


# ---------------------------------------------------------------------------
# DOCX / plain-text regex extractor
# ---------------------------------------------------------------------------

# Each pattern list is tried in order; first match wins.
# Patterns are written to handle ACORD 125/140 text as produced by
# intake.converter.docx_to_text (paragraphs + pipe-separated table rows).

_NAME_PATTERNS = [
    re.compile(r"(?:named\s+insured|applicant(?:/named\s+insured)?)\s*[:\|]\s*(.+)", re.I),
    re.compile(r"insured\s+name\s*[:\|]\s*(.+)", re.I),
]

_STATE_PATTERNS = [
    re.compile(r"\bstate\s*[:\|]\s*([A-Za-z]{2})\b", re.I),
    re.compile(r"\bwriting\s+state\s*[:\|]\s*([A-Za-z]{2})\b", re.I),
    re.compile(r",\s*([A-Z]{2})\s+\d{5}"),        # city, ST  12345
    re.compile(r"\b([A-Z]{2})\s*\|\s*\d{5}\b"),   # ST | 12345
]

_ZIP_PATTERNS = [
    re.compile(r"zip(?:\s+code)?\s*[:\|]\s*(\d{5})", re.I),
    re.compile(r"(?:postal\s+code)\s*[:\|]\s*(\d{5})", re.I),
    re.compile(r",\s*[A-Z]{2}\s+(\d{5})\b"),      # city, ST  12345
    re.compile(r"\b[A-Z]{2}\s*\|\s*(\d{5})\b"),   # ST | 12345
]

_SIC_PATTERNS = [
    re.compile(r"sic\s*(?:code)?\s*[:\|#]\s*(\d{4})\b", re.I),
    re.compile(r"business\s+classification\s+(?:code\s*)?[:\|]\s*(\d{4})\b", re.I),
    re.compile(r"nature\s+of\s+business\s*[:\|]\s*.*?(\d{4})", re.I),
    re.compile(r"\bsic\b.*?(\d{4})\b", re.I),
]

_TIV_PATTERNS = [
    re.compile(r"total\s+insured\s+value\s*[:\|]?\s*\$?([\d,\.]+)", re.I),
    re.compile(r"\btiv\b\s*[:\|]?\s*\$?([\d,\.]+)", re.I),
    re.compile(r"total\s+(?:property\s+)?limit\s*[:\|]?\s*\$?([\d,\.]+)", re.I),
]

# Additive fields — sum all matches (Building + BPP + BI)
_TIV_ADDITIVE_PATTERNS = [
    re.compile(r"building\s+(?:limit|value|insured)\s*[:\|]?\s*\$?([\d,\.]+)", re.I),
    re.compile(r"bpp\s+(?:limit|value)\s*[:\|]?\s*\$?([\d,\.]+)", re.I),
    re.compile(r"business\s+(?:personal\s+property|income)\s+limit\s*[:\|]?\s*\$?([\d,\.]+)", re.I),
    re.compile(r"contents\s+(?:limit|value)\s*[:\|]?\s*\$?([\d,\.]+)", re.I),
]

_CREDIT_YES = re.compile(
    r"credit\s+score\s+(?:used|applied|indicator)\s*[:\|]?\s*(?:yes|true|x|✓|✔|checked)",
    re.I,
)
_CREDIT_FIELD = re.compile(r"credit\s+score\s+(?:used|applied|indicator)\s*[:\|]?\s*(.+)", re.I)

_NEW_BIZ_YES = re.compile(r"(?:new\s+business|new\s+submission|quote)\s*[:\|]?\s*(?:yes|true|x|✓|✔|✗|checked|\[x\])", re.I)
_NEW_BIZ_BARE = re.compile(r"(?:^|\|)\s*new\s+business\s*(?:\||$)", re.I)
_RENEWAL_YES = re.compile(r"renewal\s*[:\|]?\s*(?:yes|true|x|✓|✔|checked|\[x\])", re.I)
_RENEWAL_BARE = re.compile(r"(?:^|\|)\s*renewal\s*(?:\||$)", re.I)


def _first_match(patterns: list[re.Pattern], text: str) -> str | None:
    for p in patterns:
        m = p.search(text)
        if m:
            return m.group(1).strip()
    return None


def extract_from_docx_text(text: str) -> dict[str, Any]:
    """Extract the 7 Jura fields from DOCX plain text using regex patterns.

    The caller is responsible for running Guard 4 (injection scan) on the text
    before calling this function.
    """
    # --- insured_name ---
    insured_name: str | None = _first_match(_NAME_PATTERNS, text)
    if insured_name:
        insured_name = insured_name.split("|")[0].strip()  # trim table artifacts
        insured_name = insured_name[:200] or None

    # --- state ---
    raw_state = _first_match(_STATE_PATTERNS, text)
    state: str | None = raw_state.upper() if raw_state else None

    # --- zip_code ---
    zip_code: str | None = _first_match(_ZIP_PATTERNS, text)

    # --- sic_code ---
    sic_code: str | None = _first_match(_SIC_PATTERNS, text)

    # --- tiv ---
    tiv = 0.0
    raw_tiv = _first_match(_TIV_PATTERNS, text)
    if raw_tiv:
        tiv = _dollars(raw_tiv)
    if tiv == 0.0:
        # Sum additive fields (building + BPP + BI)
        for p in _TIV_ADDITIVE_PATTERNS:
            for m in p.finditer(text):
                tiv += _dollars(m.group(1))

    # --- credit_score_used ---
    credit_score_used = False
    if _CREDIT_YES.search(text):
        credit_score_used = True
    else:
        m = _CREDIT_FIELD.search(text)
        if m:
            val = m.group(1).strip().lower()
            credit_score_used = val not in ("no", "false", "n", "0", "", "n/a")

    # --- new_business ---
    new_business = False
    if _NEW_BIZ_YES.search(text) or _NEW_BIZ_BARE.search(text):
        new_business = True
    elif _RENEWAL_YES.search(text) or _RENEWAL_BARE.search(text):
        new_business = False

    return {
        "insured_name": insured_name,
        "state": state,
        "zip_code": zip_code,
        "sic_code": sic_code,
        "tiv": tiv,
        "credit_score_used": credit_score_used,
        "new_business": new_business,
    }
