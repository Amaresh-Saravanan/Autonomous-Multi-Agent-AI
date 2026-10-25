"""Runner-level poller tests: HTTP is mocked (httpx.MockTransport, no real
network), DB/queue/blackboard/dedup are real test infra (fakeredis for
Redis). Covers normalization-through-ingestion, dedupe across repeated
polls, and failure isolation between sources."""

from contextlib import contextmanager
from datetime import datetime, timezone

import fakeredis
import httpx

from app.infrastructure.queue import QueueService
from app.ingestion.pollers import usgs
from app.ingestion.pollers.dedup import DedupStore
from app.ingestion.pollers.runner import PollerRunner
from app.models.incident import Event
from app.orchestration.state import BlackboardService


@contextmanager
def _fixed_session(db):
    yield db


def _runner(db, client, **overrides):
    defaults = dict(
        session_factory=lambda: _fixed_session(db),
        queue=QueueService("memory"),
        blackboard=BlackboardService(fakeredis.FakeStrictRedis(decode_responses=True)),
        dedup=DedupStore(fakeredis.FakeStrictRedis(decode_responses=True)),
        http_client=client,
        points=[("TestPoint", 10.0, 20.0)],
        bbox=(68.0, 6.0, 98.0, 38.0),
        min_magnitude=2.5,
    )
    defaults.update(overrides)
    return PollerRunner(**defaults)


OPEN_METEO_FORECAST = {
    "current": {"time": "2026-10-25T10:45", "temperature_2m": 28.0, "relative_humidity_2m": 79, "wind_speed_10m": 8.9}
}
OPEN_METEO_FLOOD = {"daily": {"river_discharge": [12.3]}}


def _open_meteo_handler(request: httpx.Request) -> httpx.Response:
    if "flood-api" in str(request.url):
        return httpx.Response(200, json=OPEN_METEO_FLOOD)
    return httpx.Response(200, json=OPEN_METEO_FORECAST)


def test_run_once_open_meteo_ingests_one_event(db):
    client = httpx.Client(transport=httpx.MockTransport(_open_meteo_handler))
    runner = _runner(db, client)

    result = runner.run_once("open_meteo")

    assert result.error is None
    assert result.ingested == 1
    events = db.query(Event).filter(Event.source_type == "weather").all()
    assert len(events) == 1
    assert events[0].payload["alert"] == "river_discharge=12.3m3/s"

    recorded = runner.status.get("open_meteo")
    assert recorded.last_count == 1
    assert recorded.last_error is None


def test_run_once_open_meteo_second_poll_dedupes(db):
    client = httpx.Client(transport=httpx.MockTransport(_open_meteo_handler))
    runner = _runner(db, client)
    runner.run_once("open_meteo")

    result2 = runner.run_once("open_meteo")

    assert result2.ingested == 0
    assert result2.skipped_duplicate == 1
    events = db.query(Event).filter(Event.source_type == "weather").all()
    assert len(events) == 1


USGS_FEED = {
    "features": [
        {"id": "big-one", "properties": {"mag": 5.0, "magType": "mb"}, "geometry": {"coordinates": [80.0, 13.0]}},
        {"id": "too-small", "properties": {"mag": 1.0, "magType": "ml"}, "geometry": {"coordinates": [80.0, 13.0]}},
        {"id": "out-of-bbox", "properties": {"mag": 6.0, "magType": "mww"}, "geometry": {"coordinates": [-116.0, 33.0]}},
    ]
}


def _usgs_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=USGS_FEED)


def test_run_once_usgs_filters_by_magnitude_and_bbox(db):
    client = httpx.Client(transport=httpx.MockTransport(_usgs_handler))
    runner = _runner(db, client)

    result = runner.run_once("usgs")

    assert result.fetched == 1
    assert result.ingested == 1
    events = db.query(Event).filter(Event.source_type == "iot").all()
    assert len(events) == 1
    assert events[0].payload["sensor_id"] == "big-one"


GDACS_TC = {
    "features": [
        {
            "properties": {"alertlevel": "Red", "eventtype": "TC", "eventid": 1, "episodeid": 1, "name": "Storm X"},
            "geometry": {"coordinates": [80.0, 13.0]},
        }
    ]
}
GDACS_EMPTY = {"features": []}


def _gdacs_handler(request: httpx.Request) -> httpx.Response:
    event_type = request.url.params.get("eventtype")
    if event_type == "TC":
        return httpx.Response(200, json=GDACS_TC)
    return httpx.Response(200, json=GDACS_EMPTY)


def test_run_once_gdacs_ingests_only_orange_red(db):
    client = httpx.Client(transport=httpx.MockTransport(_gdacs_handler))
    runner = _runner(db, client)

    result = runner.run_once("gdacs")

    assert result.ingested == 1
    events = db.query(Event).filter(Event.source_type == "weather").all()
    assert any("Storm X" in (e.payload.get("alert") or "") for e in events)


def test_run_once_isolates_failure_from_other_sources(db, monkeypatch):
    def _boom(client):
        raise RuntimeError("usgs feed unreachable")

    monkeypatch.setattr(usgs, "fetch", _boom)

    failing_client = httpx.Client(transport=httpx.MockTransport(_usgs_handler))
    runner = _runner(db, failing_client)

    result = runner.run_once("usgs")

    assert result.error is not None
    assert "unreachable" in result.error
    assert runner.status.get("usgs").last_error is not None

    # a second source on a fresh runner (same process) is unaffected
    gdacs_client = httpx.Client(transport=httpx.MockTransport(_gdacs_handler))
    other_runner = _runner(db, gdacs_client)
    other_result = other_runner.run_once("gdacs")
    assert other_result.error is None
    assert other_result.ingested == 1
