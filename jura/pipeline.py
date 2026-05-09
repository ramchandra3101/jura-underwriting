"""Pipeline registry + (best-effort) live forward to the downstream agent.

The function ``forward_to_next_agent`` does two things:

1. Always returns a dict describing where the submission is going. This is
   the part used in pure mock / offline mode.
2. **If** the result is routed to Aria **and** the ``ARIA_URL`` env var is
   set, it also makes a real ``POST`` to Aria, captures the response, and
   embeds it in the returned dict under the ``aria`` key.

Best-effort semantics: any exception (connection refused, timeout, non-2xx
response, malformed JSON, …) is caught and recorded — the caller never
sees an exception. The audit log gets ``RESPONSE_RECEIVED`` on success or
``ARIA_UNREACHABLE`` on failure (logged from ``server._evaluate``).

Env-var switches
----------------
- ``ARIA_URL``      Full URL to Aria's evaluate endpoint. When unset, no
                    live call is attempted — pure mock mode.
- ``ARIA_TIMEOUT``  Float seconds for the HTTP timeout. Default ``5.0``.
"""
from __future__ import annotations

import os

import httpx

from jura.models import JurisdictionResult


PIPELINE_REGISTRY: dict[str, dict] = {
    "aria": {
        "name": "Aria",
        "port": 8001,
        "entry_route": "/evaluate",
        "mock_url": "http://localhost:8001/evaluate",
    },
    "compliance_queue": {
        "name": "Compliance Queue",
        "port": 8002,
        "entry_route": "/queue",
        "mock_url": "http://localhost:8002/queue",
    },
    "blocked": {
        "name": "Blocked",
        "port": None,
        "entry_route": None,
        "mock_url": None,
    },
}


def _aria_url() -> str | None:
    """Live URL for Aria, or ``None`` to stay in mock mode."""
    return os.environ.get("ARIA_URL") or None


def _aria_timeout() -> float:
    try:
        return float(os.environ.get("ARIA_TIMEOUT", "5.0"))
    except ValueError:
        return 5.0


def forward_to_next_agent(result: JurisdictionResult) -> dict:
    target = PIPELINE_REGISTRY.get(result.routed_to, {})
    base: dict = {
        "forwarded": result.routed_to != "blocked",
        "target": result.routed_to,
        "submission_id": result.submission_id,
        "mock_url": target.get("mock_url"),
        "status": "queued" if result.routed_to != "blocked" else "held",
    }

    # Live call is only attempted for the Aria lane and only when ARIA_URL
    # is set. Everything else stays in pure mock mode.
    if result.routed_to == "aria":
        url = _aria_url()
        if url:
            try:
                with httpx.Client(timeout=_aria_timeout()) as client:
                    r = client.post(url, json=result.model_dump(mode="json"))
                    r.raise_for_status()
                    payload: object
                    if r.headers.get("content-type", "").startswith("application/json"):
                        payload = r.json()
                    else:
                        payload = r.text
                base["aria"] = {
                    "url": url,
                    "status_code": r.status_code,
                    "response": payload,
                }
                base["status"] = "aria_received"
            except Exception as exc:  # noqa: BLE001 — best-effort by design
                base["aria"] = {
                    "url": url,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
                base["status"] = "aria_unreachable"

    return base
