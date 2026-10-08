"""Typed ingestion request contracts (Phase 5/9). Field-level range checks
live here; cross-field business rules (bounds ordering, lat/lon pairing)
live in `validators.py`."""

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class IoTEvent(EventCreate):
    sensor_id: str
    metric: str = "unknown"
    reading: float
    unit: str = ""
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class WeatherEvent(EventCreate):
    location: str = "unknown"
    temp_c: float | None = None
    humidity_pct: float | None = None
    wind_speed_kmh: float | None = None
    alert: str | None = None
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class SatelliteEvent(EventCreate):
    image_id: str
    date: str | None = None
    cloud_cover_pct: float | None = None
    resolution_m: float = 10
    area_bounds: list[float] = Field(min_length=4, max_length=4)


class CitizenReport(EventCreate):
    reporter_contact: str | None = None
    message: str
    claimed_severity: float = Field(default=0.5, ge=0.0, le=1.0)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    incident_id: str | None = None


class IngestAccepted(BaseModel):
    event_id: str
    incident_id: str
    status: str = "accepted"
