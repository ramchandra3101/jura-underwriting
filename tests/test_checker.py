"""Jurisdiction checker tests — all deterministic, no LLM calls."""
from __future__ import annotations

import pytest

from jura.checker import run_jurisdiction_check
from jura.models import JurisdictionBlock, SubmissionEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _event(**overrides) -> SubmissionEvent:
    defaults = dict(
        submission_id="TEST-001",
        insured_name="Acme Corp",
        sic_code="5812",
        state="TX",
        zip_code="73301",
        tiv=500_000.0,
        credit_score_used=False,
        new_business=True,
    )
    defaults.update(overrides)
    return SubmissionEvent(**defaults)


# ---------------------------------------------------------------------------
# 1. TX admitted — market=admitted, routed to aria, no active flags
# ---------------------------------------------------------------------------

def test_tx_admitted_clear():
    result = run_jurisdiction_check(_event(state="TX"))
    assert result.market == "admitted"
    assert result.eligible is True
    assert result.has_block is False
    assert result.routed_to == "aria"
    # tx_surplus_threshold not triggered (TIV 500k < 5M threshold)
    assert not any(f.level == "block" for f in result.doi_flags)


# ---------------------------------------------------------------------------
# 2. CA non-FAIR-Plan ZIP + credit_score_used → ca_ab2414 disclose flag
#    ZIP 94102 (SF, prefix "941" — not in wildfire FAIR Plan list).
# ---------------------------------------------------------------------------

def test_ca_credit_disclose():
    result = run_jurisdiction_check(
        _event(
            submission_id="TEST-CA-CREDIT",
            state="CA",
            zip_code="94102",
            credit_score_used=True,
        )
    )
    disclose_ids = {f.rule_id for f in result.doi_flags if f.level == "disclose"}
    assert "ca_ab2414" in disclose_ids
    assert result.has_disclose is True
    assert result.has_block is False


# ---------------------------------------------------------------------------
# 3. FL ZIP 33139 (Miami Beach) → JurisdictionBlock raised (moratorium)
# ---------------------------------------------------------------------------

def test_fl_moratorium_raises():
    with pytest.raises(JurisdictionBlock) as exc_info:
        run_jurisdiction_check(
            _event(
                state="FL",
                zip_code="33139",
            )
        )
    assert "moratorium" in exc_info.value.reason.lower()
    assert "627.351" in exc_info.value.statutory_ref


# ---------------------------------------------------------------------------
# 4. CA ZIP in FAIR Plan prefix → JurisdictionBlock raised
#    ZIP 91901 starts with "919" which is in ca_fair_plan_zips.
# ---------------------------------------------------------------------------

def test_ca_fair_plan_zip_raises():
    with pytest.raises(JurisdictionBlock) as exc_info:
        run_jurisdiction_check(
            _event(
                state="CA",
                zip_code="91901",
            )
        )
    assert "FAIR Plan" in exc_info.value.reason or "fair" in exc_info.value.reason.lower()
    assert "10091" in exc_info.value.statutory_ref


# ---------------------------------------------------------------------------
# 5. NY + credit_score_used → block flag ny_part86
#    market="blocked", eligible=False, routed_to="blocked"
# ---------------------------------------------------------------------------

def test_ny_credit_block():
    result = run_jurisdiction_check(
        _event(
            state="NY",
            zip_code="10001",
            credit_score_used=True,
        )
    )
    block_ids = {f.rule_id for f in result.doi_flags if f.level == "block"}
    assert "ny_part86" in block_ids
    assert result.has_block is True
    assert result.eligible is False
    assert result.market == "blocked"
    assert result.routed_to == "blocked"


# ---------------------------------------------------------------------------
# 6. CA non-FAIR-Plan ZIP, no credit score → clean admitted result
# ---------------------------------------------------------------------------

def test_ca_clean_admitted():
    result = run_jurisdiction_check(
        _event(
            state="CA",
            zip_code="94102",
            credit_score_used=False,
        )
    )
    assert result.market == "admitted"
    assert result.has_block is False
    assert result.eligible is True


# ---------------------------------------------------------------------------
# 7. TX TIV $6M → market=es, warn flag tx_surplus_threshold triggered
#    Routed to compliance_queue (surplus threshold exceeded)
# ---------------------------------------------------------------------------

def test_tx_high_tiv_surplus():
    result = run_jurisdiction_check(
        _event(
            state="TX",
            tiv=6_000_000.0,
        )
    )
    warn_ids = {f.rule_id for f in result.doi_flags if f.level == "warn"}
    assert "tx_surplus_threshold" in warn_ids
    assert result.market == "es"
    assert result.routed_to == "compliance_queue"


# ---------------------------------------------------------------------------
# 8. eligible computed field — True for admitted, False for blocked
# ---------------------------------------------------------------------------

def test_eligible_admitted_clear():
    result = run_jurisdiction_check(_event(state="TX"))
    assert result.eligible is True


def test_eligible_false_for_blocked():
    result = run_jurisdiction_check(
        _event(
            state="NY",
            zip_code="10001",
            credit_score_used=True,
        )
    )
    assert result.eligible is False
    assert result.market == "blocked"


# ---------------------------------------------------------------------------
# 9. FL non-moratorium ZIP with property coverage → sinkhole disclose flag
# ---------------------------------------------------------------------------

def test_fl_sinkhole_disclose():
    result = run_jurisdiction_check(
        _event(
            state="FL",
            zip_code="32200",
        )
    )
    disclose_ids = {f.rule_id for f in result.doi_flags if f.level == "disclose"}
    assert "fl_sinkhole" in disclose_ids
    assert result.has_disclose is True


# ---------------------------------------------------------------------------
# 10. NY new_business=True → free-look period notice (disclose flag)
# ---------------------------------------------------------------------------

def test_ny_new_business_disclose():
    result = run_jurisdiction_check(
        _event(
            state="NY",
            zip_code="10001",
            credit_score_used=False,
            new_business=True,
        )
    )
    disclose_ids = {f.rule_id for f in result.doi_flags if f.level == "disclose"}
    assert "ny_free_look" in disclose_ids
    assert result.has_disclose is True
