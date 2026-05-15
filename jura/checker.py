from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from jura.mock_data import (
    ADMITTED_STATES,
    CA_FAIR_PLAN_ZIPS,
    DOI_RULES,
    FL_MORATORIUM_ZIPS,
    LA_COAST_ZIPS,
    NJ_COAST_ZIPS,
    NC_COAST_ZIPS,
    SC_COAST_ZIPS,
    SURPLUS_LINES,
    TX_TWIA_ZIPS,
)
from jura.models import (
    DOIFlag,
    JurisdictionBlock,
    JurisdictionResult,
    MultiStateConflict,
    SubmissionEvent,
)


# ---------------------------------------------------------------------------
# ZIP proxy objects for eval() context
# ---------------------------------------------------------------------------

class _MoratoriumZipProxy:
    def __contains__(self, zip5: str) -> bool:
        return is_moratorium_zip(zip5)


class _FairPlanZipProxy:
    def __contains__(self, zip5: str) -> bool:
        return is_fair_plan_zip(zip5)


class _TwiaTxZipProxy:
    def __contains__(self, zip5: str) -> bool:
        return zip5 in TX_TWIA_ZIPS


class _LaCoastZipProxy:
    def __contains__(self, zip5: str) -> bool:
        return zip5 in LA_COAST_ZIPS


class _NjCoastZipProxy:
    def __contains__(self, zip5: str) -> bool:
        return zip5 in NJ_COAST_ZIPS


class _NcCoastZipProxy:
    def __contains__(self, zip5: str) -> bool:
        return zip5 in NC_COAST_ZIPS


class _ScCoastZipProxy:
    def __contains__(self, zip5: str) -> bool:
        return zip5 in SC_COAST_ZIPS


# ---------------------------------------------------------------------------
# Public lookup functions
# ---------------------------------------------------------------------------

def is_fair_plan_zip(zip5: str) -> bool:
    return zip5[:3] in CA_FAIR_PLAN_ZIPS


def is_moratorium_zip(zip5: str) -> bool:
    return zip5 in FL_MORATORIUM_ZIPS


def evaluate_doi_rules(state: str, event: SubmissionEvent) -> list[DOIFlag]:
    rules = DOI_RULES.get(state) or []
    admitted = state in ADMITTED_STATES["admitted"]

    ctx: dict = {
        # event fields
        "credit_score_used": event.credit_score_used,
        "new_business": event.new_business,
        "property_coverage": True,
        "writing_state": event.state,
        "mailing_state": event.state,
        "premises_zip": event.zip_code,
        "tiv": event.tiv or 0.0,
        "sic_code": event.sic_code,
        # derived
        "admitted_market": admitted,
        # YAML boolean literals
        "true": True,
        "false": False,
        # State-code constants — all 50 states + DC
        "AL": "AL", "AK": "AK", "AZ": "AZ", "AR": "AR", "CA": "CA",
        "CO": "CO", "CT": "CT", "DE": "DE", "FL": "FL", "GA": "GA",
        "HI": "HI", "ID": "ID", "IL": "IL", "IN": "IN", "IA": "IA",
        "KS": "KS", "KY": "KY", "LA": "LA", "ME": "ME", "MD": "MD",
        "MA": "MA", "MI": "MI", "MN": "MN", "MS": "MS", "MO": "MO",
        "MT": "MT", "NE": "NE", "NV": "NV", "NH": "NH", "NJ": "NJ",
        "NM": "NM", "NY": "NY", "NC": "NC", "ND": "ND", "OH": "OH",
        "OK": "OK", "OR": "OR", "PA": "PA", "RI": "RI", "SC": "SC",
        "SD": "SD", "TN": "TN", "TX": "TX", "UT": "UT", "VT": "VT",
        "VA": "VA", "WA": "WA", "WV": "WV", "WI": "WI", "WY": "WY",
        "DC": "DC",
        # ZIP set proxies
        "CA_FAIR_PLAN_ZIPS": _FairPlanZipProxy(),
        "FL_MORATORIUM_ZIPS": _MoratoriumZipProxy(),
        "TX_TWIA_ZIPS": _TwiaTxZipProxy(),
        "LA_COAST_ZIPS": _LaCoastZipProxy(),
        "NJ_COAST_ZIPS": _NjCoastZipProxy(),
        "NC_COAST_ZIPS": _NcCoastZipProxy(),
        "SC_COAST_ZIPS": _ScCoastZipProxy(),
    }

    flags: list[DOIFlag] = []
    for rule in rules:
        try:
            triggered = bool(eval(rule["trigger_condition"], {"__builtins__": {}}, ctx))  # noqa: S307
        except Exception:
            triggered = False

        level: str = rule["type"] if triggered else "clear"
        flags.append(
            DOIFlag(
                rule_id=rule["id"],
                rule_name=rule["name"],
                level=level,
                state=state,
                statutory_ref=rule["statutory_ref"],
                disclosure_template=rule.get("disclosure_template"),
                description=(
                    f"{rule['name']}: rule triggered ({rule['statutory_ref']})"
                    if triggered
                    else f"{rule['name']}: not triggered"
                ),
            )
        )

    return flags


def _surplus_threshold(state: str) -> float | None:
    state_cfg = (SURPLUS_LINES.get("thresholds") or {}).get(state)
    if not state_cfg:
        return None
    return float(state_cfg["tiv_threshold"])


def check_surplus_eligible(state: str, event: SubmissionEvent) -> bool:
    if state not in ADMITTED_STATES["surplus_lines_licensed"]:
        return False

    state_cfg = (SURPLUS_LINES.get("thresholds") or {}).get(state)
    if not state_cfg:
        return True  # licensed, no threshold defined

    tiv_ok = (event.tiv or 0.0) > state_cfg["tiv_threshold"]
    sic_ok = event.sic_code in [str(s) for s in state_cfg.get("eligible_sics", [])]
    return tiv_ok or sic_ok


def generate_es_mock_declinations(state: str, sic: str) -> list[dict]:
    return [
        {"carrier": "Mock Carrier A", "declined_reason": "Outside appetite"},
        {"carrier": "Mock Carrier B", "declined_reason": "TIV too high"},
        {"carrier": "Mock Carrier C", "declined_reason": "Geographic restriction"},
    ]


# Re-exported from jura.notices to keep the evaluation engine free of file I/O.
from jura.notices import _write_disclosure_doc  # noqa: E402,F401


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def _build_rationale(
    market: str,
    state: str,
    tiv: float,
    blocked_reason: str | None,
    n_disclose: int,
) -> str:
    if market == "blocked":
        return f"Submission blocked. {blocked_reason}. Statutory hold issued."
    if market == "es":
        return (
            f"Submission routed to E&S market. "
            f"TIV of ${tiv:,.0f} exceeds surplus threshold for {state}."
        )
    if n_disclose > 0:
        return (
            f"Submission cleared for admitted market in {state}. "
            f"{n_disclose} disclosure flag(s) require compliance review "
            f"before forwarding to appetite scoring."
        )
    return (
        f"Submission cleared for admitted market in {state}. "
        f"No DOI flags triggered. Forwarding to appetite scoring."
    )


def run_jurisdiction_check(event: SubmissionEvent) -> JurisdictionResult:
    state = event.state

    # Hard geo-block checks — raise immediately (kept for backward compat with
    # existing tests; the route layer catches these and converts to a result).
    if state == "FL" and is_moratorium_zip(event.zip_code):
        raise JurisdictionBlock(
            reason=f"FL coastal moratorium applies to ZIP {event.zip_code}",
            statutory_ref="FL Ins Code §627.351",
            broker_notice_template="fl_moratorium_notice.txt",
        )
    if state == "CA" and is_fair_plan_zip(event.zip_code):
        raise JurisdictionBlock(
            reason=f"CA FAIR Plan wildfire zone: ZIP {event.zip_code} (prefix {event.zip_code[:3]})",
            statutory_ref="CA Ins Code §10091",
            broker_notice_template="ca_fair_plan_notice.txt",
        )

    # Evaluate DOI rules for the writing state
    doi_flags = evaluate_doi_rules(state, event)

    # Routing logic
    block_flags = [f for f in doi_flags if f.level == "block"]
    disclose_flags = [f for f in doi_flags if f.level == "disclose"]
    threshold = _surplus_threshold(state)

    if block_flags:
        market = "blocked"
        routed_to = "blocked"
        blocked_reason = block_flags[0].statutory_ref
    elif threshold is not None and event.tiv > threshold:
        market = "es"
        routed_to = "compliance_queue"
        blocked_reason = None
    elif disclose_flags:
        # Requires human disclosure review before Aria forwarding.
        market = "admitted"
        routed_to = "compliance_queue"
        blocked_reason = None
    else:
        market = "admitted"
        routed_to = "aria"
        blocked_reason = None

    rationale = _build_rationale(
        market=market,
        state=state,
        tiv=event.tiv,
        blocked_reason=blocked_reason,
        n_disclose=len(disclose_flags),
    )

    return JurisdictionResult(
        submission_id=event.submission_id,
        insured_name=event.insured_name,
        market=market,
        doi_flags=doi_flags,
        rationale=rationale,
        routed_to=routed_to,
        blocked_reason=blocked_reason,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
