from __future__ import annotations

import threading
from typing import Any

_DRAFTS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()


def upsert(draft_id: str, draft: dict[str, Any]) -> None:
    with _LOCK:
        _DRAFTS[draft_id] = draft


def get(draft_id: str) -> dict[str, Any] | None:
    return _DRAFTS.get(draft_id)


def list_all() -> list[dict[str, Any]]:
    return list(_DRAFTS.values())


def patch_fields(draft_id: str, fields: dict[str, Any]) -> dict[str, Any] | None:
    with _LOCK:
        draft = _DRAFTS.get(draft_id)
        if draft is None:
            return None
        _DRAFTS[draft_id] = {**draft, "fields": {**draft["fields"], **fields}}
        return _DRAFTS[draft_id]


def patch_validation(draft_id: str, status: str, validation: dict) -> None:
    with _LOCK:
        if draft_id in _DRAFTS:
            _DRAFTS[draft_id]["status"] = status
            _DRAFTS[draft_id]["validation"] = validation


def mark_confirmed(draft_id: str) -> None:
    with _LOCK:
        if draft_id in _DRAFTS:
            _DRAFTS[draft_id]["status"] = "confirmed"


def delete(draft_id: str) -> bool:
    with _LOCK:
        return _DRAFTS.pop(draft_id, None) is not None


def clear() -> None:
    with _LOCK:
        _DRAFTS.clear()
