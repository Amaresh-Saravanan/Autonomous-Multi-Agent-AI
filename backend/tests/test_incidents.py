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


def test_same_district_far_apart_share_incident(monkeypatch):
    """District-based clustering: events >5km apart but in the same district
    should merge into one incident (district beats distance)."""
    incidents.reset()

    def fake_geocode(lat, lon):
        # All coordinates return the same district
        return ("Tamil Nadu", "Chennai District")

    from app import geocode
    monkeypatch.setattr(geocode, "reverse", fake_geocode)

    a = incidents.assign_incident(_event(80.27, 13.08))  # Chennai
    b = incidents.assign_incident(_event(80.27, 14.08))  # ~111km away, same district
    assert a == b  # Same incident


def test_different_districts_close_together_separate_incidents(monkeypatch):
    """District-based clustering: events <5km apart but in different districts
    should NOT merge (district overrides proximity)."""
    incidents.reset()

    call_count = [0]

    def fake_geocode(lat, lon):
        # Alternate which district each call returns
        call_count[0] += 1
        if call_count[0] == 1:
            return ("Tamil Nadu", "Chennai District")
        else:
            return ("Tamil Nadu", "Kanchipuram District")

    from app import geocode
    monkeypatch.setattr(geocode, "reverse", fake_geocode)

    a = incidents.assign_incident(_event(80.270, 13.080))  # Chennai District
    b = incidents.assign_incident(_event(80.275, 13.085))  # ~0.8km away, different district
    assert a != b  # Separate incidents


def test_same_district_outside_time_window_separate_incidents(monkeypatch):
    """District-based clustering: same district but outside WINDOW_SECONDS
    should NOT merge (time window still closes out stale incidents)."""
    incidents.reset()

    def fake_geocode(lat, lon):
        return ("Tamil Nadu", "Chennai District")

    from app import geocode
    monkeypatch.setattr(geocode, "reverse", fake_geocode)

    a = incidents.assign_incident(_event(80.27, 13.08, "2026-08-16T10:00:00+00:00"))
    b = incidents.assign_incident(_event(80.27, 13.08, "2026-08-16T12:00:00+00:00"))  # +2h
    assert a != b  # Stale, separate incidents


def test_fallback_to_distance_time_on_geocode_failure(monkeypatch):
    """When geocoding returns (None, None), fall back to distance+time logic
    unchanged (verifies the old 5km/1hr window behavior still works)."""
    incidents.reset()

    # Explicitly use the autouse fixture's fallback: (None, None)
    # (This is already set by conftest.py, but we can also verify it here)
    from app import geocode
    monkeypatch.setattr(geocode, "reverse", lambda lat, lon: (None, None))

    a = incidents.assign_incident(_event(80.270, 13.080))
    b = incidents.assign_incident(_event(80.275, 13.085))  # ~0.8km away
    assert a == b  # Falls back to distance+time clustering


