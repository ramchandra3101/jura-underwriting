"""Jurisdiction checker tests — all deterministic, no LLM calls."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import pytest

from jura.checker import (
    run_jurisdiction_check,
)
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
# 1. TX admitted — market=admitted, no active flags
# ---------------------------------------------------------------------------

def test_tx_admitted_clear():
    result = run_jurisdiction_check(_event(state="TX"))
    assert result.market == "admitted"
    assert result.admitted is True
    assert result.eligible is True
    assert result.has_block is False
    active = [f for f in result.doi_flags if f.level != "clear"]
    # tx_surplus_threshold not triggered (TIV 500k < 5M)
    assert not any(f.level == "block" for f in active)


# ---------------------------------------------------------------------------
# 2. CA non-FAIR-Plan ZIP + credit_score_used → ca_ab2414 disclose flag
#    Using ZIP 94102 (SF, prefix "941" — not in wildfire FAIR Plan list).
# ---------------------------------------------------------------------------

def test_ca_credit_disclose():
    result = run_jurisdiction_check(
        _event(
            submission_id="TEST-CA-CREDIT",
            state="CA",
            zip_code="94102",   # San Francisco — prefix 941, not a FAIR Plan zone
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
                zip_code="91901",   # prefix 919 — Malibu/Pacific Palisades zone
            )
        )
    assert "FAIR Plan" in exc_info.value.reason or "fair" in exc_info.value.reason.lower()
    assert "10091" in exc_info.value.statutory_ref


# ---------------------------------------------------------------------------
# 5. NY + credit_score_used → block flag ny_part86, eligible=False
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
    assert result.market == "restricted"


# ---------------------------------------------------------------------------
# 6. CA/NV multi-state → multi_state=True detected
# ---------------------------------------------------------------------------

def test_ca_nv_multi_state():
    result = run_jurisdiction_check(
        _event(
            state="CA",
            zip_code="94102",   # SF — not a FAIR Plan or moratorium zip
        )
    )
    assert result.multi_state is True
    jd = detect_jurisdiction(
        _event(state="CA")
    )
    assert jd["multi_state"] is True


# ---------------------------------------------------------------------------
# 7. TX TIV $6M → es_eligible=True, warn flag tx_surplus_threshold
# ---------------------------------------------------------------------------

def test_tx_high_tiv_surplus_warn():
    result = run_jurisdiction_check(
        _event(
            state="TX",
            tiv=6_000_000.0,
        )
    )
    warn_ids = {f.rule_id for f in result.doi_flags if f.level == "warn"}
    assert "tx_surplus_threshold" in warn_ids
    assert result.es_eligible is True


# ---------------------------------------------------------------------------
# 8. eligible=True for admitted-clear, False for restricted
# ---------------------------------------------------------------------------

def test_eligible_admitted_clear():
    result = run_jurisdiction_check(_event(state="TX"))
    assert result.eligible is True


def test_eligible_false_for_restricted():
    result = run_jurisdiction_check(
        _event(
            state="NY",
            zip_code="10001",
            credit_score_used=True,
        )
    )
    assert result.eligible is False
    assert result.market == "restricted"


# ---------------------------------------------------------------------------
# 9. Disclosure doc written to data/disclosures/ for disclose flag
# ---------------------------------------------------------------------------

def test_disclosure_doc_written():
    result = run_jurisdiction_check(
        _event(
            submission_id="TEST-DISC-001",
            state="CA",
            zip_code="94102",
            credit_score_used=True,
        )
    )
    assert result.has_disclose is True
    assert len(result.disclosure_docs) > 0
    for path in result.disclosure_docs:
        assert Path(path).exists(), f"Disclosure doc not found: {path}"
        assert "TEST-DISC-001" in Path(path).name
