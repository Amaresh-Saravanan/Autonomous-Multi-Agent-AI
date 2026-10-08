"""IoT normalizer (Phase 9, ported from V1 `normalize_iot`). A deployed
sensor reports its own fixed location, so it is always EXACT — never
UNKNOWN or approximate."""

from app.ingestion.schemas import IoTEvent
from app.models.incident import LocationStateEnum


def normalize_iot(data: IoTEvent) -> dict:
    return {
        "source_type": "iot",
        "payload": {"sensor_id": data.sensor_id, "metric": data.metric, "reading": data.reading, "unit": data.unit},
        "location_state": LocationStateEnum.EXACT,
        "latitude": data.lat,
        "longitude": data.lon,
        "confidence": data.confidence,
    }
