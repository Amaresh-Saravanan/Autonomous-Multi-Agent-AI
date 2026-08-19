"""Incident clustering (tracker 1.9): turn a stream of raw events into
confirmed incidents.

Raw sensor events don't know which incident they belong to — the platform
decides. `assign_incident` greedily attaches an event to the nearest open
incident within a distance radius AND a recency window, or mints a new
incident if none is close enough. This is what lets the system say "these
events are one disaster" without a client dictating incident_id.

ponytail: in-memory registry, greedy nearest-match (O(n) scan of open
incidents), no persistence — fine for a single-process dev server. Upgrade
to a spatial index + a DB-backed incident store (with incident close-out) when
event volume or a multi-worker deployment demands it. Only point-geometry
events cluster; polygon events (e.g. satellite tiles) each get their own
incident until centroid-based clustering is needed.
"""
from __future__ import annotations

import time
from datetime import datetime

from .geo_utils import distance_km
from .models import Event

RADIUS_KM = 5.0          # an event within this distance of an open incident joins it
WINDOW_SECONDS = 3600    # ...and within this time of that incident's latest event

# incident_id -> {"lat", "lon", "last_ts" (epoch seconds), "count"}
_incidents: dict[str, dict] = {}


def _parse_ts(ts: str) -> float:
    try:
        return datetime.fromisoformat(ts).timestamp()
    except (ValueError, TypeError):
        return time.time()


def _point(event: Event) -> tuple[float, float] | None:
    """Return (lon, lat) for a Point event, else None (non-point geometry)."""
    coords = event.geo.coordinates
    if isinstance(coords, list) and len(coords) == 2 and all(
        isinstance(c, (int, float)) for c in coords
    ):
        return float(coords[0]), float(coords[1])
    return None


def _new_incident(lat: float | None, lon: float | None, ts: float) -> str:
    incident_id = f"incident-{len(_incidents) + 1}"
    _incidents[incident_id] = {"lat": lat, "lon": lon, "last_ts": ts, "count": 1}
    return incident_id


def assign_incident(event: Event) -> str:
    """Attach `event` to an existing open incident (spatial + temporal
    proximity) or create a new one. Returns the incident_id."""
    ts = _parse_ts(event.timestamp)
    point = _point(event)
    if point is None:
        # No usable point geometry -> can't cluster spatially; give it its own.
        return _new_incident(None, None, ts)

    lon, lat = point
    best_id: str | None = None
    best_dist = RADIUS_KM
    for incident_id, inc in _incidents.items():
        if inc["lat"] is None or ts - inc["last_ts"] > WINDOW_SECONDS:
            continue
        d = distance_km(lon, lat, inc["lon"], inc["lat"])
        if d <= best_dist:
            best_id, best_dist = incident_id, d

    if best_id is not None:
        inc = _incidents[best_id]
        inc["last_ts"] = max(inc["last_ts"], ts)
        inc["count"] += 1
        return best_id

    return _new_incident(lat, lon, ts)


def reset() -> None:
    """Clear the registry (test isolation; also a fresh-process reset)."""
    _incidents.clear()
