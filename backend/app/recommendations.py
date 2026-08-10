"""In-memory recommendation store + status transitions (tracker 2.9, PRD AC-5).
Mirrors blackboard.py's in-memory pattern — no DB needed to run.
"""
from __future__ import annotations

_recs: dict[str, dict] = {}


def record(rec: dict) -> None:
    _recs[rec["rec_id"]] = rec


def get(rec_id: str) -> dict | None:
    return _recs.get(rec_id)


def list_recs(status: str | None = None) -> list[dict]:
    recs = list(_recs.values())
    if status:
        recs = [r for r in recs if r["status"] == status]
    return recs
