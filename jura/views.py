"""Legacy HTML route stubs.

The original implementation rendered Jinja templates (queue.html, blocks.html,
audit_log.html, insights.html) backed by SQLite + JSONL files. The Phase B
rewrite moved Jura to an in-memory dict store, which is incompatible with
those templates — every render call dies inside Jinja2's cache lookup with
``TypeError: unhashable type: 'dict'``.

The templates and the router itself are deliberately kept on disk and
registered, per the original spec ("do not delete the templates/ folder
or any HTML UI routes"). What changed: each handler now returns a small
JSON status object instead of attempting to render the broken template.
That keeps the routes reachable and stops them flooding the launcher logs
with stack traces.

For the live demo, use the playground (``Nexus/playground/index.html``)
or the auto-generated Swagger UI at ``/docs``.
"""
from __future__ import annotations

from fastapi import APIRouter


router = APIRouter(tags=["ui"])


def _retired(route: str) -> dict:
    return {
        "status": "retired",
        "route": route,
        "note": (
            "The legacy HTML browser UI was retired when Jura moved to "
            "in-memory storage. Use the JSON API (see /docs) or the "
            "Nexus playground instead."
        ),
        "alternatives": {
            "swagger":    "/docs",
            "submissions": "/submissions",
            "audit":      "/audit/{submission_id}",
            "results":    "/results",
        },
    }


@router.get("/")
def get_root() -> dict:
    return _retired("/")


@router.get("/blocks")
def get_blocks() -> dict:
    return _retired("/blocks")


# Note: /audit/{submission_id} is the JSON route on the main app; the
# bare /audit and /audit/export below cover the legacy HTML URLs only.
@router.get("/audit/export")
def get_audit_export() -> dict:
    return _retired("/audit/export")


@router.get("/insights")
def get_insights() -> dict:
    return _retired("/insights")


@router.get("/w2c/jurisdiction")
def w2c_info() -> dict:
    return {
        "endpoint": "POST /jurisdiction",
        "description": "W2-C jurisdiction check — submit SubmissionEvent JSON body",
        "schema": "See POST /jurisdiction · OpenAPI at /docs",
    }
