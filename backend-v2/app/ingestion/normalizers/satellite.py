"""Satellite normalizer (Phase 9, ported from V1 `normalize_satellite`).
A satellite tile covers an area, not a point — the centroid is an
APPROXIMATE location, never EXACT (Phase 13: don't overclaim precision)."""

from app.ingestion.schemas import SatelliteEvent
from app.ingestion.validators import validate_bounds
from app.models.incident import LocationStateEnum


def normalize_satellite(data: SatelliteEvent) -> dict:
    validate_bounds(data.area_bounds)
    min_lon, min_lat, max_lon, max_lat = data.area_bounds
    center_lon = (min_lon + max_lon) / 2
    center_lat = (min_lat + max_lat) / 2
    return {
        "source_type": "satellite",
        "payload": {
            "image_id": data.image_id,
            "date": data.date,
            "cloud_cover_pct": data.cloud_cover_pct,
            "resolution_m": data.resolution_m,
            "area_bounds": data.area_bounds,
        },
        "location_state": LocationStateEnum.APPROXIMATE,
        "latitude": center_lat,
        "longitude": center_lon,
        "confidence": data.confidence,
    }
