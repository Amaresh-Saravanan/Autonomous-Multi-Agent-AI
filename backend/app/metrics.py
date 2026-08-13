"""In-process request metrics (tracker 3.8): counts + latency per route.

ponytail: in-process, single-worker, resets on restart, no persistence,
naive percentile (sorted-list index). Upgrade path is prometheus_client +
a real scrape target if/when an ops stack exists.
"""
from __future__ import annotations

from collections import deque

_MAX_SAMPLES = 200

# route -> {"count": int, "latencies": deque[float]}
_routes: dict[str, dict] = {}


def record(route: str, duration_ms: float) -> None:
    entry = _routes.setdefault(route, {"count": 0, "latencies": deque(maxlen=_MAX_SAMPLES)})
    entry["count"] += 1
    entry["latencies"].append(duration_ms)


def _percentile(sorted_values: list[float], pct: float) -> float:
    idx = min(len(sorted_values) - 1, int(len(sorted_values) * pct))
    return sorted_values[idx]


def summary() -> dict:
    routes = {}
    for route, entry in _routes.items():
        latencies = sorted(entry["latencies"])
        routes[route] = {
            "count": entry["count"],
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0.0,
            "p95_latency_ms": _percentile(latencies, 0.95) if latencies else 0.0,
        }
    return {"routes": routes}
