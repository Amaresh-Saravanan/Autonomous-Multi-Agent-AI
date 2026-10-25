"""Pure mapping-function and dedup-store tests for the data pollers --
no network, no DB. Fetch/HTTP is covered with a mocked transport in
tests/integration/test_poller_runner.py."""

import fakeredis

from app.ingestion.pollers import gdacs, open_meteo, usgs
from app.ingestion.pollers.dedup import DedupStore
from app.ingestion.schemas import IoTEvent, WeatherEvent


def test_open_meteo_build_event_maps_fields_and_folds_flood_into_alert():
    forecast = {"current": {"time": "2026-10-25T10:45", "temperature_2m": 28.0, "relative_humidity_2m": 79, "wind_speed_10m": 8.9}}
    flood = {"daily": {"river_discharge": [123.4]}}

    event, dedup_id = open_meteo.build_event("Chennai", 13.08, 80.27, forecast, flood)

    assert isinstance(event, WeatherEvent)
    assert event.location == "Chennai"
    assert event.temp_c == 28.0
    assert event.humidity_pct == 79
    assert event.wind_speed_kmh == 8.9
    assert event.alert == "river_discharge=123.4m3/s"
    assert event.lat == 13.08 and event.lon == 80.27
    assert dedup_id == "Chennai:2026-10-25T10:45"


def test_open_meteo_build_event_no_flood_data_leaves_alert_none():
    forecast = {"current": {"time": "2026-10-25T10:45", "temperature_2m": 28.0}}
    event, _ = open_meteo.build_event("Mumbai", 19.07, 72.87, forecast, {})
    assert event.alert is None


def test_usgs_build_event_maps_fields():
    feature = {
        "id": "ci41352127",
        "properties": {"mag": 4.2, "magType": "ml"},
        "geometry": {"type": "Point", "coordinates": [-116.39, 33.35, 13.1]},
    }
    result = usgs.build_event(feature)
    assert result is not None
    event, dedup_id = result
    assert isinstance(event, IoTEvent)
    assert event.sensor_id == "ci41352127"
    assert event.metric == "magnitude"
    assert event.reading == 4.2
    assert event.unit == "ml"
    assert event.lat == 33.35 and event.lon == -116.39
    assert dedup_id == "ci41352127"


def test_usgs_build_event_returns_none_without_magnitude():
    feature = {"id": "x", "properties": {"mag": None}, "geometry": {"coordinates": [1.0, 2.0]}}
    assert usgs.build_event(feature) is None


def test_usgs_in_bbox():
    bbox = (68.0, 6.0, 98.0, 38.0)
    assert usgs._in_bbox(80.0, 13.0, bbox) is True
    assert usgs._in_bbox(-116.0, 33.0, bbox) is False


def test_gdacs_build_event_filters_green_alert_level():
    feature = {
        "properties": {"alertlevel": "Green", "eventtype": "TC", "eventid": 1, "episodeid": 1, "name": "x"},
        "geometry": {"type": "Point", "coordinates": [-65.8, 40.0]},
    }
    assert gdacs.build_event(feature) is None


def test_gdacs_build_event_maps_orange_and_red():
    feature = {
        "properties": {
            "alertlevel": "Red",
            "eventtype": "TC",
            "eventid": 1001342,
            "episodeid": 5,
            "name": "Tropical Cyclone JOSEPHINE-26",
            "severitydata": {"severitytext": "Tropical Storm (maximum wind speed of 120 km/h)"},
        },
        "geometry": {"type": "Point", "coordinates": [-65.8, 40.0]},
    }
    result = gdacs.build_event(feature)
    assert result is not None
    event, dedup_id = result
    assert isinstance(event, WeatherEvent)
    assert event.lat == 40.0 and event.lon == -65.8
    assert "Red TC" in event.alert
    assert "JOSEPHINE-26" in event.alert
    assert dedup_id == "TC:1001342:5"


def test_dedup_store_marks_and_detects_duplicates():
    store = DedupStore("redis", fakeredis.FakeStrictRedis(decode_responses=True))
    assert store.already_seen("usgs", "evt-1") is False
    store.mark_seen("usgs", "evt-1")
    assert store.already_seen("usgs", "evt-1") is True
    # different source, same id -- not a duplicate across sources
    assert store.already_seen("gdacs", "evt-1") is False


def test_dedup_store_memory_mode_works_without_redis():
    """QUEUE_BACKEND=memory local dev: no Redis client, no Redis server."""
    store = DedupStore("memory")
    assert store.already_seen("usgs", "evt-1") is False
    store.mark_seen("usgs", "evt-1")
    assert store.already_seen("usgs", "evt-1") is True
    assert store.already_seen("gdacs", "evt-1") is False


def test_dedup_store_memory_mode_rejects_redis_backend_without_client():
    import pytest

    from app.errors import QueueError

    with pytest.raises(QueueError):
        DedupStore("redis")


def test_gdacs_fetch_event_type_does_not_retry_404():
    """A 404 means this eventtype doesn't exist -- permanent, not
    transient -- so it must fail on the first attempt, not after 3."""
    import httpx

    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(404, json={"message": "not found"})

    client = httpx.Client(transport=httpx.MockTransport(handler))

    try:
        gdacs.fetch_event_type(client, "VO")
        assert False, "expected HTTPStatusError"
    except httpx.HTTPStatusError:
        pass

    assert call_count == 1


def test_gdacs_fetch_event_type_retries_non_404_errors():
    """A non-404 (e.g. 503) is transient -- still retried up to 3 attempts."""
    import httpx

    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(503, json={"message": "unavailable"})

    client = httpx.Client(transport=httpx.MockTransport(handler))

    try:
        gdacs.fetch_event_type(client, "EQ")
        assert False, "expected HTTPStatusError"
    except httpx.HTTPStatusError:
        pass

    assert call_count == 3


def test_gdacs_event_types_excludes_vo():
    assert "VO" not in gdacs.EVENT_TYPES
