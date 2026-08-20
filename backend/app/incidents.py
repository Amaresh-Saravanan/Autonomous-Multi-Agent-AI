"""Incident clustering (tracker 1.9): turn a stream of raw events into
confirmed incidents.

Raw sensor events don't know which incident they belong to — the platform
decides via a two-level model: events in the same DISTRICT within a time
window are clustered into one incident (districts are the real grouping unit;
states ride along as rollup labels). Reverse geocoding resolves (lat, lon) to
(state, district) via Nominatim (free, no API key, ~1req/sec courtesy limit).

Fallback: if geocoding fails/unavailable, reverts to the old distance+time
logic (5km radius, 1hr time window) so the system works offline. This matches
the codebase-wide convention (llm.py, blackboard.py) that no code hard-depends
on an external service.

Only point-geometry events cluster; polygon events (e.g. satellite tiles)
each get their own incident.

ponytail: in-memory registry, O(n) scan of open incidents, no persistence —
fine for a single-process dev server. Upgrade to a spatial index + a DB-backed
incident store (with incident close-out) when event volume or a multi-worker
deployment demands it.
"""
from __future__ import annotations

import time
from datetime import datetime

from . import geocode
from .geo_utils import distance_km
from .models import Event

RADIUS_KM = 5.0          # fallback: an event within this distance of an open incident joins it
WINDOW_SECONDS = 3600    # ...and within this time of that incident's latest event

# incident_id -> {"lat", "lon", "last_ts" (epoch seconds), "count", "state", "district"}
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


def _register(
    incident_id: str,
    lat: float | None,
    lon: float | None,
    ts: float,
    state: str | None = None,
    district: str | None = None,
) -> None:
    _incidents[incident_id] = {
        "lat": lat,
        "lon": lon,
        "last_ts": ts,
        "count": 1,
        "state": state,
        "district": district,
    }


def _new_incident(
    lat: float | None,
    lon: float | None,
    ts: float,
    state: str | None = None,
    district: str | None = None,
) -> str:
    incident_id = f"incident-{len(_incidents) + 1}"
    _register(incident_id, lat, lon, ts, state, district)
    return incident_id


def touch(incident_id: str, event: Event) -> None:
    """Register/refresh `incident_id` in the registry when it was supplied
    explicitly by the caller (bypassing assign_incident's clustering, which
    is the only other writer). Without this, explicit-id incidents — most of
    real traffic, since callers usually already know their incident_id — were
    invisible to GET /incidents (BE-1) and never got state/district
    blackboard enrichment. Call only for explicit ids; assign_incident's own
    path already registers itself."""
    ts = _parse_ts(event.timestamp)
    if incident_id in _incidents:
        inc = _incidents[incident_id]
        inc["last_ts"] = max(inc["last_ts"], ts)
        inc["count"] += 1
        return
    point = _point(event)
    if point is None:
        _register(incident_id, None, None, ts)
        return
    lon, lat = point
    state, district = geocode.reverse(lat, lon)
    _register(incident_id, lat, lon, ts, state, district)


def assign_incident(event: Event) -> str:
    """Attach `event` to an existing open incident (district-based with
    fallback to spatial+temporal proximity) or create a new one. Returns incident_id."""
    ts = _parse_ts(event.timestamp)
    point = _point(event)
    if point is None:
        # No usable point geometry -> can't cluster; give it its own.
        return _new_incident(None, None, ts, state=None, district=None)

    lon, lat = point
    state, district = geocode.reverse(lat, lon)

    if district is not None:
        # District-clustering path: same district + within time window = same incident
        for incident_id, inc in _incidents.items():
            if (
                inc["district"] == district
                and ts - inc["last_ts"] <= WINDOW_SECONDS
            ):
                inc["last_ts"] = max(inc["last_ts"], ts)
                inc["count"] += 1
                return incident_id
        return _new_incident(lat, lon, ts, state, district)

    # Fallback path: geocoding unavailable/failed -> distance+time logic (unchanged)
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

    return _new_incident(lat, lon, ts, state=None, district=None)


def reset() -> None:
    """Clear the registry and geocode cache (test isolation; also a fresh-process reset)."""
    _incidents.clear()
    geocode.reset()


def get(incident_id: str) -> dict | None:
    """Return the incident's state/district + other fields, or None if not found."""
    return _incidents.get(incident_id)


def list_incidents() -> list[dict]:
    """All known incidents, newest-activity-first (tracker 3.11.6.2 / BE-1)."""
    return [
        {"incident_id": incident_id, **inc}
        for incident_id, inc in sorted(
            _incidents.items(), key=lambda kv: kv[1]["last_ts"], reverse=True
        )
    ]
