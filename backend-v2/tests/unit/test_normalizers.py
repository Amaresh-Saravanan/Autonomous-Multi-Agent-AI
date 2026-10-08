import pytest

from app.ingestion.normalizers.citizen import normalize_citizen, score_confidence
from app.ingestion.normalizers.iot import normalize_iot
from app.ingestion.normalizers.satellite import normalize_satellite
from app.ingestion.normalizers.weather import normalize_weather
from app.ingestion.schemas import CitizenReport, IoTEvent, SatelliteEvent, WeatherEvent
from app.errors import ValidationError
from app.models.incident import LocationStateEnum


def test_iot_normalizer_is_exact_location():
    event = IoTEvent(sensor_id="wl-42", metric="water_level", reading=4.8, unit="m", lat=13.08, lon=80.27)
    result = normalize_iot(event)
    assert result["location_state"] == LocationStateEnum.EXACT
    assert result["payload"]["reading"] == 4.8


def test_weather_normalizer_is_exact_location():
    event = WeatherEvent(location="Chennai", temp_c=32, lat=13.08, lon=80.27)
    result = normalize_weather(event)
    assert result["location_state"] == LocationStateEnum.EXACT


def test_satellite_normalizer_centroid_is_approximate():
    event = SatelliteEvent(image_id="s2-1", area_bounds=[80.2, 13.0, 80.3, 13.1])
    result = normalize_satellite(event)
    assert result["location_state"] == LocationStateEnum.APPROXIMATE
    assert result["latitude"] == pytest.approx(13.05)
    assert result["longitude"] == pytest.approx(80.25)


def test_satellite_normalizer_rejects_inverted_bounds():
    event = SatelliteEvent(image_id="s2-1", area_bounds=[80.3, 13.1, 80.2, 13.0])
    with pytest.raises(ValidationError):
        normalize_satellite(event)


def test_citizen_normalizer_without_coords_is_unknown():
    report = CitizenReport(message="water rising fast")
    result = normalize_citizen(report)
    assert result["location_state"] == LocationStateEnum.UNKNOWN
    assert result["latitude"] is None


def test_citizen_normalizer_with_coords_is_approximate_not_exact():
    report = CitizenReport(message="water rising fast", lat=13.08, lon=80.27)
    result = normalize_citizen(report)
    assert result["location_state"] == LocationStateEnum.APPROXIMATE


def test_score_confidence_first_report_is_neutral():
    confidence, flagged = score_confidence(0.7, {})
    assert confidence == 0.5
    assert flagged is False


def test_score_confidence_corroborating_claim():
    confidence, flagged = score_confidence(0.75, {"AG-1": {"severity": 0.7}})
    assert confidence == 0.8
    assert flagged is False


def test_score_confidence_divergent_claim_is_flagged():
    confidence, flagged = score_confidence(0.9, {"AG-1": {"severity": 0.2}})
    assert confidence == 0.2
    assert flagged is True
