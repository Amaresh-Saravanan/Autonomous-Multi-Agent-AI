"""Weather normalizer (Phase 9, ported from V1 `normalize_weather`). A
weather station/feed reports a fixed station location — EXACT."""

from app.ingestion.schemas import WeatherEvent
from app.models.incident import LocationStateEnum


def normalize_weather(data: WeatherEvent) -> dict:
    return {
        "source_type": "weather",
        "payload": {
            "location": data.location,
            "temp_c": data.temp_c,
            "humidity_pct": data.humidity_pct,
            "wind_speed_kmh": data.wind_speed_kmh,
            "alert": data.alert,
        },
        "location_state": LocationStateEnum.EXACT,
        "latitude": data.lat,
        "longitude": data.lon,
        "confidence": data.confidence,
    }
