"""In-memory submission store.

Replaces the SQLite implementation. The four required public methods are
``get``, ``upsert``, ``list_all``, and ``seed``. Legacy method names
(``get_submission``, ``list_submissions``, ``update_status`` …) remain as
no-op or pass-through shims so the existing HTML routes don't crash on
page load — they simply see an empty/legacy view.
"""
from __future__ import annotations


_STORE: dict[str, dict] = {}


_SEED: list[dict] = [
    {
        "submission_id": "SUB-001",
        "insured_name": "Rossi's Italian Kitchen",
        "state": "IL",
        "zip_code": "60601",
        "sic_code": "5812",
        "tiv": 450000.0,
        "credit_score_used": False,
        "new_business": True,
    },
    {
        "submission_id": "SUB-002",
        "insured_name": "Patel Food Markets",
        "state": "FL",
        "zip_code": "33139",
        "sic_code": "5411",
        "tiv": 820000.0,
        "credit_score_used": False,
        "new_business": True,
    },
    {
        "submission_id": "SUB-003",
        "insured_name": "Harbor View Lounge",
        "state": "CA",
        "zip_code": "90210",
        "sic_code": "5813",
        "tiv": 620000.0,
        "credit_score_used": True,
        "new_business": False,
    },
    {
        "submission_id": "SUB-004",
        "insured_name": "Apex Business Services",
        "state": "NY",
        "zip_code": "10001",
        "sic_code": "7374",
        "tiv": 310000.0,
        "credit_score_used": True,
        "new_business": True,
    },
    {
        "submission_id": "SUB-005",
        "insured_name": "Greenberg Builders",
        "state": "TX",
        "zip_code": "75001",
        "sic_code": "1731",
        "tiv": 6200000.0,
        "credit_score_used": False,
        "new_business": True,
    },
]


class SubmissionDB:
    """Thin handle over the module-level ``_STORE`` dict."""

    # ------------------------------------------------------------------
    # Required API
    # ------------------------------------------------------------------

    def get(self, submission_id: str) -> dict | None:
        return _STORE.get(submission_id)

    def upsert(self, row: dict) -> None:
        _STORE[row["submission_id"]] = dict(row)

    def list_all(self) -> list[dict]:
        return list(_STORE.values())

    def seed(self) -> None:
        _STORE.clear()
        for row in _SEED:
            self.upsert(row)

    # ------------------------------------------------------------------
    # Legacy shims — keep existing HTML routes from crashing.
    # These return empty / pass-through results; they are not used by the
    # new /evaluate, /results, /demo/* pipeline.
    # ------------------------------------------------------------------

    def get_submission(self, submission_id: str) -> dict | None:
        row = self.get(submission_id)
        if row is None:
            return None
        # Adapt to the legacy column names used by templates.
        return {
            "id": row["submission_id"],
            "named_insured": row["insured_name"],
            "sic_code": row["sic_code"],
            "sic_description": "",
            "writing_state": row["state"],
            "mailing_state": row["state"],
            "premises_zip": row["zip_code"],
            "tiv": row.get("tiv"),
            "credit_score_used": int(bool(row.get("credit_score_used", False))),
            "pc_account_id": "",
            "status": row.get("status", "jura_pending"),
            "market": row.get("market"),
            "jurisdiction_outcome": row.get("jurisdiction_outcome"),
            "created_at": row.get("created_at", ""),
        }

    def list_submissions(self, status: str | None = None, limit: int = 20) -> list[dict]:
        rows = [self.get_submission(r["submission_id"]) for r in _STORE.values()]
        rows = [r for r in rows if r is not None]
        if status:
            rows = [r for r in rows if r["status"] == status]
        return rows[:limit]

    def get_compliance_queue(self) -> list[dict]:
        return self.list_submissions(status="admitted_disclose_pending", limit=100)

    def get_blocks(self) -> list[dict]:
        return self.list_submissions(status="jurisdiction_blocked", limit=100)

    def insert_submission(self, data: dict) -> None:
        # Legacy callers pass old-shape rows. Best effort: store under id.
        sid = data.get("submission_id") or data.get("id")
        if not sid:
            return
        _STORE[sid] = {
            "submission_id": sid,
            "insured_name": data.get("named_insured", data.get("insured_name", "")),
            "state": data.get("writing_state", data.get("state", "")),
            "zip_code": data.get("premises_zip", data.get("zip_code", "")),
            "sic_code": data.get("sic_code", ""),
            "tiv": data.get("tiv", 0.0) or 0.0,
            "credit_score_used": bool(data.get("credit_score_used", False)),
            "new_business": bool(data.get("new_business", True)),
            "status": data.get("status", "jura_pending"),
            "market": data.get("market"),
            "jurisdiction_outcome": data.get("jurisdiction_outcome"),
        }

    def update_status(self, submission_id: str, status: str) -> None:
        if submission_id in _STORE:
            _STORE[submission_id]["status"] = status

    def update_market(self, submission_id: str, market: str) -> None:
        if submission_id in _STORE:
            _STORE[submission_id]["market"] = market

    def seed_sample_data(self) -> None:
        self.seed()

    def clear_submissions(self) -> None:
        _STORE.clear()


# Legacy import name kept for back-compat with anything that still references
# the SQLite status set; treated as informational.
VALID_STATUSES: set[str] = {
    "jura_pending",
    "jura_checking",
    "admitted_clear",
    "admitted_disclose_pending",
    "admitted_disclose_approved",
    "surplus_pending",
    "surplus_confirmed",
    "multi_state_conflict",
    "jurisdiction_blocked",
    "forwarded_to_aria",
    "aria_pending_retry",
    "compliance_escalated",
}
