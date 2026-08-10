"""Shared agent state (TDD 3.3). In-memory by default; Redis if REDIS_URL is set
and reachable. No install/credential required to run.
"""
from __future__ import annotations
import json
import os

_mem: dict[str, dict] = {}
_r = None

if os.getenv("REDIS_URL"):
    try:
        import redis  # type: ignore
        _r = redis.from_url(os.environ["REDIS_URL"], socket_connect_timeout=1)
        _r.ping()
    except Exception:  # noqa: BLE001 - any failure => in-memory fallback
        _r = None


def _key(incident_id: str) -> str:
    return f"incident:{incident_id}"


def get(incident_id: str) -> dict:
    if _r is not None:
        raw = _r.get(_key(incident_id))
        return json.loads(raw) if raw else {}
    return _mem.get(incident_id, {})


def merge(incident_id: str, patch: dict) -> dict:
    state = get(incident_id)
    state.update(patch)
    if _r is not None:
        _r.set(_key(incident_id), json.dumps(state))
    else:
        _mem[incident_id] = state
    return state


def using_redis() -> bool:
    return _r is not None
