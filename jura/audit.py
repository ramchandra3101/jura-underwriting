"""In-memory tamper-evident audit log.

Replaces the JSONL-on-disk implementation. ``AUDIT_LOG`` is the single source
of truth; every entry carries a SHA-256 ``log_hash`` over the canonical JSON
of the payload (excluding the hash itself), and an ``event_type`` tag.

Event types
-----------
- ``EVALUATED``         clean pass or disclose-only result
- ``BLOCKED``           any block flag result (or JurisdictionBlock raised)
- ``FORWARDED``         after ``forward_to_next_agent`` is called
- ``DISCLOSE_QUEUED``   result whose ``doi_flags`` contain a disclose flag
- ``RESPONSE_RECEIVED`` Aria returned a 2xx response to the live forward
- ``ARIA_UNREACHABLE``  Aria call attempted but failed (timeout / 5xx / refused)
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any

from jura.models import JurisdictionResult


# A6 — guards every audit append
_lock = threading.Lock()

# B3 — single in-memory list, replacing the JSONL file
AUDIT_LOG: list[dict] = []


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def _hash_payload(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _result_payload(result: JurisdictionResult, insured_name: str) -> dict:
    return {
        "submission_id": result.submission_id,
        "insured_name": insured_name or result.insured_name,
        "market": result.market,
        "routed_to": result.routed_to,
        "blocked_reason": result.blocked_reason,
        "eligible": result.eligible,
        "doi_flags": [
            {
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "level": f.level,
                "statutory_ref": f.statutory_ref,
            }
            for f in result.doi_flags
        ],
        "has_block": result.has_block,
        "has_disclose": result.has_disclose,
        "timestamp": result.timestamp,
    }


def _append(event_type: str, payload: dict) -> dict:
    entry: dict = {"event_type": event_type, **payload}
    entry["log_hash"] = _hash_payload(entry)
    with _lock:
        AUDIT_LOG.append(entry)
    return entry


# ---------------------------------------------------------------------------
# Public logger
# ---------------------------------------------------------------------------

class _MissingPath:
    """Stand-in for the old JSONL paths so legacy HTML routes don't crash.

    Exposes ``.exists()`` returning ``False`` and a falsy bool so any
    ``if path.exists():`` or ``open(path)`` guarded by an existence check
    short-circuits without raising.
    """

    def exists(self) -> bool:
        return False

    def __bool__(self) -> bool:
        return False


class JurisdictionAuditLogger:
    """All logger methods are stateless wrappers around module-level state.

    The class is kept so existing dependency-injection points
    (``app.state.audit``) continue to work unchanged.
    """

    # Legacy attribute referenced by HTML routes (compliance/review.py,
    # jura/views.py). The audit log is fully in-memory now, so this points
    # at a stub that reports "doesn't exist" to short-circuit any reads.
    log_path = _MissingPath()
    compliance_log_path = _MissingPath()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def log_jurisdiction(
        self,
        result: JurisdictionResult,
        insured_name: str = "",
    ) -> None:
        payload = _result_payload(result, insured_name)
        if result.has_block or result.market == "blocked":
            event_type = "BLOCKED"
        elif result.has_disclose:
            event_type = "DISCLOSE_QUEUED"
        else:
            event_type = "EVALUATED"
        _append(event_type, payload)

    def log_blocked(
        self,
        submission_id: str,
        insured_name: str,
        blocked_reason: str,
        statutory_ref: str,
        timestamp: str | None = None,
    ) -> None:
        """B5 — used when JurisdictionBlock is caught before a result exists."""
        payload = {
            "submission_id": submission_id,
            "insured_name": insured_name,
            "market": "blocked",
            "routed_to": "blocked",
            "blocked_reason": blocked_reason,
            "statutory_ref": statutory_ref,
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        }
        _append("BLOCKED", payload)

    def log_forwarded(
        self,
        submission_id: str,
        target: str,
        forward_meta: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "submission_id": submission_id,
            "target": target,
            "forward_meta": forward_meta or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _append("FORWARDED", payload)

    def log_response_received(
        self,
        submission_id: str,
        target: str,
        status_code: int,
        response: Any,
    ) -> None:
        payload = {
            "submission_id": submission_id,
            "target": target,
            "status_code": status_code,
            "response": response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _append("RESPONSE_RECEIVED", payload)

    def log_unreachable(
        self,
        submission_id: str,
        target: str,
        url: str,
        error: str,
        error_type: str,
    ) -> None:
        payload = {
            "submission_id": submission_id,
            "target": target,
            "url": url,
            "error": error,
            "error_type": error_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        _append("ARIA_UNREACHABLE", payload)

    def log_compliance_decision(
        self,
        submission_id: str,
        reviewer_id: str,
        choice: str,
        notes: str,
    ) -> None:
        payload = {
            "submission_id": submission_id,
            "reviewer_id": reviewer_id,
            "choice": choice,
            "notes": notes,
            "decided_at": datetime.now(timezone.utc).isoformat(),
        }
        _append("DISCLOSE_QUEUED" if choice != "approve" else "FORWARDED", payload)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def all(self) -> list[dict]:
        with _lock:
            return list(AUDIT_LOG)

    def events_for(self, submission_id: str) -> list[dict]:
        with _lock:
            return [e for e in AUDIT_LOG if e.get("submission_id") == submission_id]

    def read_jurisdiction_log(self, submission_id: str | None = None) -> list[dict]:
        with _lock:
            if submission_id is None:
                return list(AUDIT_LOG)
            return [e for e in AUDIT_LOG if e.get("submission_id") == submission_id]

    def clear(self) -> None:
        with _lock:
            AUDIT_LOG.clear()

    def verify_integrity(self) -> dict:
        with _lock:
            entries = list(AUDIT_LOG)
        if not entries:
            return {"status": "no_log", "total": 0, "valid": 0, "invalid": 0, "errors": []}
        total = valid = invalid = 0
        errors: list[dict] = []
        for i, raw in enumerate(entries, 1):
            total += 1
            entry = dict(raw)
            stored = entry.pop("log_hash", None)
            if _hash_payload(entry) == stored:
                valid += 1
            else:
                invalid += 1
                errors.append({
                    "line": i,
                    "submission_id": entry.get("submission_id"),
                    "error": "hash_mismatch",
                })
        return {
            "status": "ok" if invalid == 0 else "integrity_errors",
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "errors": errors,
        }
