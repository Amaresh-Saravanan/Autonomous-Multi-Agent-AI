"""Append-only audit log (TDD 3.2 audit_log, SEC-2). In-memory for now, wired
only to the approve/reject endpoints (tracker 2.9/AC-5). Full coverage across
every state-changing endpoint is tracker 1.11, deferred to Phase 3.
"""
from __future__ import annotations
from datetime import datetime, timezone

_log: list[dict] = []


def record(actor: str, action: str, target: str, before: dict, after: dict) -> dict:
    entry = {
        "actor": actor,
        "action": action,
        "target": target,
        "before": dict(before),  # snapshot — caller's dict may mutate later
        "after": dict(after),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _log.append(entry)
    return entry


def all_entries() -> list[dict]:
    return list(_log)
