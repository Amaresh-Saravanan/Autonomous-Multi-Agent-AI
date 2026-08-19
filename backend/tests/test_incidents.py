"""Incident clustering (tracker 1.9): raw events with no client-supplied
incident_id are grouped into confirmed incidents by spatial-temporal
proximity, so the platform assigns incident_ids itself instead of trusting
whatever the caller sends.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from fastapi.testclient import TestClient
from app.main import app
from app import incidents
from app.models import Event, Geo

client = TestClient(app)


def _event(lon: float, lat: float, timestamp: str = "2026-08-16T10:00:00+00:00") -> Event:
    return Event(
        source_type="iot",
        source_id="wl-1",
        geo=Geo(type="Point", coordinates=[lon, lat]),
        timestamp=timestamp,
    )


def test_events_close_in_space_and_time_share_an_incident():
    incidents.reset()
    a = incidents.assign_incident(_event(80.270, 13.080))
    b = incidents.assign_incident(_event(80.275, 13.085))  # ~0.8km away, same time
    assert a == b


def test_events_far_apart_get_separate_incidents():
    incidents.reset()
    a = incidents.assign_incident(_event(80.27, 13.08))
    b = incidents.assign_incident(_event(80.27, 14.08))  # ~111km away
    assert a != b


def test_events_outside_time_window_get_separate_incidents():
    incidents.reset()
    a = incidents.assign_incident(_event(80.27, 13.08, "2026-08-16T10:00:00+00:00"))
    b = incidents.assign_incident(_event(80.27, 13.08, "2026-08-16T12:00:00+00:00"))  # +2h
    assert a != b


def test_ingest_without_incident_id_clusters_by_location():
    incidents.reset()
    r1 = client.post("/ingest/iot", json={
        "sensor_id": "wl-1", "metric": "water_level", "reading": 5.5,
        "unit": "m", "lat": 13.080, "lon": 80.270,
    }).json()
    r2 = client.post("/ingest/iot", json={
        "sensor_id": "wl-2", "metric": "water_level", "reading": 5.6,
        "unit": "m", "lat": 13.085, "lon": 80.275,
    }).json()
    assert r1["incident_id"] == r2["incident_id"]


def test_ingest_honors_explicit_incident_id():
    incidents.reset()
    r = client.post("/ingest/iot", json={
        "sensor_id": "wl-1", "metric": "water_level", "reading": 5.5,
        "unit": "m", "lat": 13.08, "lon": 80.27, "incident_id": "explicit-1",
    }).json()
    assert r["incident_id"] == "explicit-1"
