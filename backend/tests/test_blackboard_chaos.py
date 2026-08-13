"""Chaos/resilience test (tracker 3.7): proves blackboard.py's silent
Redis-fallback actually holds when REDIS_URL points at an unreachable host,
not just that the code looks like it should work.
"""
import importlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from app import blackboard  # noqa: E402


def test_merge_and_get_round_trip_when_redis_unreachable(monkeypatch):
    # TEST-NET-1 (RFC 5737): reserved, guaranteed unreachable, won't hit a real host.
    monkeypatch.setenv("REDIS_URL", "redis://192.0.2.1:6399")
    importlib.reload(blackboard)
    try:
        assert blackboard.using_redis() is False

        blackboard.merge("test-incident", {"foo": "bar"})
        assert blackboard.get("test-incident") == {"foo": "bar"}
    finally:
        # Reload back to a clean module state so we don't leak into other
        # tests in this session (app.main imports this module directly).
        monkeypatch.delenv("REDIS_URL", raising=False)
        importlib.reload(blackboard)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
