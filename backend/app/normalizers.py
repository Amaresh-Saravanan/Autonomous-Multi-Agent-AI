"""Source-specific normalizers -> common Event schema (TDD 3.1, PRD DI-7).

Phase 0 ships one normalizer (IoT). Add satellite/weather/etc. in Phase 1
following the same shape: raw payload in, Event out.
"""
from __future__ import annotations
from .models import Event, Geo
from . import blackboard
from . import citizen_reports
from . import citizen_verification


def normalize_iot(raw: dict) -> Event:
    """raw example: {"sensor_id": "wl-042", "reading": 4.8, "unit": "m",
    "metric": "water_level", "lat": 13.0827, "lon": 80.2707}"""
    return Event(
        source_type="iot",
        source_id=str(raw["sensor_id"]),
        geo=Geo(type="Point", coordinates=[raw["lon"], raw["lat"]]),
        payload={
            "metric": raw.get("metric", "unknown"),
            "reading": raw["reading"],
            "unit": raw.get("unit", ""),
        },
        confidence=float(raw.get("confidence", 1.0)),
    )


def normalize_weather(raw: dict) -> Event:
    """raw example: {"location": "Chennai", "temp": 32, "humidity": 85,
    "wind_speed": 45, "lat": 13.08, "lon": 80.27, "alert": "cyclone"}"""
    return Event(
        source_type="weather",
        source_id=str(raw.get("location", "unknown")),
        geo=Geo(type="Point", coordinates=[raw["lon"], raw["lat"]]),
        payload={
            "temp_c": raw.get("temp"),
            "humidity_pct": raw.get("humidity"),
            "wind_speed_kmh": raw.get("wind_speed"),
            "alert": raw.get("alert"),
        },
        confidence=float(raw.get("confidence", 0.95)),
    )


def normalize_satellite(raw: dict) -> Event:
    """raw example: {"image_id": "s2-tile-001", "date": "2026-07-24",
    "cloud_cover": 5, "area_bounds": [80.2, 13.0, 80.3, 13.1]}"""
    bounds = raw.get("area_bounds", [80.27, 13.08, 80.27, 13.08])
    center_lon = (bounds[0] + bounds[2]) / 2
    center_lat = (bounds[1] + bounds[3]) / 2
    return Event(
        source_type="satellite",
        source_id=str(raw["image_id"]),
        geo=Geo(
            type="Polygon",
            coordinates=[[[bounds[0], bounds[1]], [bounds[2], bounds[1]],
                          [bounds[2], bounds[3]], [bounds[0], bounds[3]],
                          [bounds[0], bounds[1]]]],
        ),
        payload={
            "date": raw.get("date"),
            "cloud_cover_pct": raw.get("cloud_cover"),
            "resolution_m": raw.get("resolution_m", 10),
        },
        confidence=float(raw.get("confidence", 0.9)),
    )


def normalize_citizen(raw: dict) -> Event:
    """raw example: {"reporter_id": "citizen-1", "claimed_severity": 0.65,
    "message": "...", "lat": 13.08, "lon": 80.27, "incident_id": "inc-1"}

    Does NOT wake any orchestrator agent (tracker 3.3 design doc) — only
    computes a trust/confidence score against AG-1's current severity.
    """
    incident_id = raw.get("incident_id", "default")  # matches main.py's /ingest fallback
    state = blackboard.get(incident_id)
    claimed_severity = float(raw.get("claimed_severity", 0.5))
    confidence, flagged = citizen_verification.score_confidence(
        incident_id, claimed_severity, state
    )
    event = Event(
        source_type="citizen",
        source_id=str(raw.get("reporter_id", "unknown")),
        geo=Geo(type="Point", coordinates=[raw["lon"], raw["lat"]]),
        payload={
            "message": raw.get("message", ""),
            "claimed_severity": claimed_severity,
            "flagged_for_review": flagged,
        },
        confidence=confidence,
    )
    citizen_reports.record({
        "event_id": event.event_id,
        "incident_id": incident_id,
        "reporter_id": event.source_id,
        "message": event.payload["message"],
        "claimed_severity": claimed_severity,
        "confidence": confidence,
        "flagged_for_review": flagged,
        "timestamp": event.timestamp,
    })
    return event


NORMALIZERS = {
    "iot": normalize_iot,
    "weather": normalize_weather,
    "satellite": normalize_satellite,
    "citizen": normalize_citizen,
}


def normalize(source_type: str, raw: dict) -> Event:
    fn = NORMALIZERS.get(source_type)
    if fn is None:
        raise ValueError(f"no normalizer registered for source_type={source_type!r}")
    return fn(raw)
