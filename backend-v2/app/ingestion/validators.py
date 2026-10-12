"""Cross-field ingestion validation (Phase 8/9). Field-level range checks
already happen in `schemas.py`; this is for rules that span multiple
fields and don't fit a single Pydantic `Field(...)` constraint."""

from app.errors import ValidationError


def validate_bounds(bounds: list[float]) -> None:
    min_lon, min_lat, max_lon, max_lat = bounds
    if not (min_lon < max_lon and min_lat < max_lat):
        raise ValidationError(
            "area_bounds must be [min_lon, min_lat, max_lon, max_lat] with min < max",
            details={"area_bounds": bounds},
        )
