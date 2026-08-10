"""Source-specific normalizers -> common Event schema (TDD 3.1, PRD DI-7).

Phase 0 ships one normalizer (IoT). Add satellite/weather/etc. in Phase 1
following the same shape: raw payload in, Event out.
"""
from __future__ import annotations
from .models import Event, Geo


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


NORMALIZERS = {
    "iot": normalize_iot,
    "weather": normalize_weather,
    "satellite": normalize_satellite,
}


def normalize(source_type: str, raw: dict) -> Event:
    fn = NORMALIZERS.get(source_type)
    if fn is None:
        raise ValueError(f"no normalizer registered for source_type={source_type!r}")
    return fn(raw)
