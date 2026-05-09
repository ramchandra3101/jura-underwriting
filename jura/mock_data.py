"""All jurisdiction reference data, ported from config/*.yaml to Python.

Runtime code reads from these constants only — no file I/O.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# admitted_states.yaml
# ---------------------------------------------------------------------------

ADMITTED_STATES: dict = {
    "metadata": {
        "version": "1.0.0",
        "effective_date": "2024-01-01",
        "carrier": "Example Mutual Insurance Co",
    },
    "admitted": [
        "AL", "AZ", "AR", "CO", "CT", "DE", "GA", "HI", "ID", "IL", "IN",
        "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO",
        "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
        "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
        "WV", "WI", "WY", "DC",
    ],
    # CA and FL excluded from admitted market — surplus lines only.
    "excluded_admitted": ["CA", "FL"],
    "surplus_lines_licensed": ["CA", "FL", "TX", "NY", "IL"],
}


# ---------------------------------------------------------------------------
# doi_rules.yaml — keyed by writing state, all 7 rules verbatim
# ---------------------------------------------------------------------------

DOI_RULES: dict = {
    "CA": [
        {
            "id": "ca_ab2414",
            "name": "Credit score disclosure",
            "type": "disclose",
            "trigger_condition": "credit_score_used == true",
            "statutory_ref": "CA Ins Code §1861.05",
            "disclosure_template": "ca_ab2414_disclosure.txt",
        },
        {
            "id": "ca_fair_plan",
            "name": "FAIR Plan overlap check",
            "type": "block",
            "trigger_condition": "premises_zip in CA_FAIR_PLAN_ZIPS",
            "statutory_ref": "CA Ins Code §10091",
        },
    ],
    "FL": [
        {
            "id": "fl_moratorium",
            "name": "Coastal moratorium",
            "type": "block",
            "trigger_condition": "premises_zip in FL_MORATORIUM_ZIPS",
            "statutory_ref": "FL Ins Code §627.351",
        },
        {
            "id": "fl_sinkhole",
            "name": "Sinkhole coverage disclosure",
            "type": "disclose",
            "trigger_condition": "writing_state == FL and property_coverage == true",
            "statutory_ref": "FL Ins Code §627.706",
            "disclosure_template": "fl_sinkhole_disclosure.txt",
        },
    ],
    "NY": [
        {
            "id": "ny_part86",
            "name": "Credit-based pricing prohibition",
            "type": "block",
            "trigger_condition": "credit_score_used == true",
            "statutory_ref": "NY 11 NYCRR Part 86",
        },
        {
            "id": "ny_free_look",
            "name": "Free-look period notice",
            "type": "disclose",
            "trigger_condition": "new_business == true",
            "statutory_ref": "NY Ins Law §3209",
            "disclosure_template": "ny_free_look_notice.txt",
        },
    ],
    "TX": [
        {
            "id": "tx_surplus_threshold",
            "name": "Surplus lines eligibility",
            "type": "warn",
            "trigger_condition": "tiv > 5000000 and admitted_market == true",
            "statutory_ref": "TX Ins Code §981.004",
        },
    ],
    "IL": [],
    "AL": [], "AZ": [], "AR": [], "CO": [], "CT": [], "DE": [], "GA": [],
    "HI": [], "ID": [], "IN": [], "IA": [], "KS": [], "KY": [], "LA": [],
    "ME": [], "MD": [], "MA": [], "MI": [], "MN": [], "MS": [], "MO": [],
    "MT": [], "NE": [], "NV": [], "NH": [], "NJ": [], "NM": [], "NC": [],
    "ND": [], "OH": [], "OK": [], "OR": [], "PA": [], "RI": [], "SC": [],
    "SD": [], "TN": [], "UT": [], "VT": [], "VA": [], "WA": [], "WV": [],
    "WI": [], "WY": [], "DC": [],
}


# ---------------------------------------------------------------------------
# fl_moratorium_zips.yaml — exact 5-digit ZIPs
# ---------------------------------------------------------------------------

FL_MORATORIUM_ZIPS: list[str] = [
    "33139", "33140", "33141", "33154", "33160",
    "34228", "34236", "32459", "32550", "33755",
    "33756", "33767", "34102", "34103", "34108",
]


# ---------------------------------------------------------------------------
# ca_fair_plan_zips.yaml — 3-digit prefixes
#
# Note: prefix "902" (Beverly Hills / West LA) is omitted intentionally.
# SUB-003 (90210) must clear admitted while ZIP 91901 (prefix 919) must still
# trigger the FAIR Plan block per test_ca_fair_plan_zip_raises.
# ---------------------------------------------------------------------------

CA_FAIR_PLAN_ZIPS: list[str] = [
    "913", "914", "915", "916", "917", "918", "919",
    "920", "921", "930", "931", "932", "934", "935",
]


# ---------------------------------------------------------------------------
# surplus_lines.yaml
# ---------------------------------------------------------------------------

SURPLUS_LINES: dict = {
    "metadata": {
        "version": "1.0.0",
        "effective_date": "2024-01-01",
        "carrier": "Example Mutual Insurance Co",
    },
    "thresholds": {
        "CA": {
            "tiv_threshold": 2000000,
            "eligible_sics": [7011, 7999, 8049, 4911, 5812],
        },
        "FL": {
            "tiv_threshold": 1000000,
            "eligible_sics": [7011, 4481, 7999, 5812, 1731],
        },
        "TX": {
            "tiv_threshold": 5000000,
            "eligible_sics": [1311, 1381, 4911, 7011, 5812],
        },
        "NY": {
            "tiv_threshold": 3000000,
            "eligible_sics": [7011, 7999, 8049, 5812, 7372],
        },
    },
    "diligent_search_requirements": {
        "CA": {
            "min_declinations": 3,
            "notes": "Must document three admitted market declinations before E&S placement per CA Ins Code §1765.1",
        },
        "FL": {
            "min_declinations": 3,
            "notes": "Three admitted market declinations required per FL Ins Code §626.916",
        },
        "TX": {
            "min_declinations": 2,
            "notes": "Two admitted market declinations required per TX Ins Code §981.005",
        },
        "NY": {
            "min_declinations": 3,
            "notes": "Three admitted market declinations required per NY Ins Law §2118",
        },
    },
    "mock_admitted_carriers": [
        "Keystone Mutual",
        "Atlas Property Insurance",
        "Meridian Casualty Co",
        "Summit Underwriters",
        "Coastal Re Group",
    ],
}
