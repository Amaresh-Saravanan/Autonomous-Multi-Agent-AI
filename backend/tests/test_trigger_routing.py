"""Trigger routing (tracker 2.1 remaining half, PRD AC-2): not every agent
runs on every event. Ground-truth sensor readings (iot) trigger the full
response chain; satellite imagery only triggers assessment + damage;
weather forecasts only trigger assessment + situational summary — no
dispatch agent should fire off a forecast alone.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_iot_event_still_runs_the_full_chain():
    r = client.post("/ingest/iot", json={
        "sensor_id": "wl-trig-1", "metric": "water_level", "reading": 6.0, "unit": "m",
        "lat": 13.08, "lon": 80.27, "incident_id": "trigger-iot-1",
    })
    assert r.status_code == 200
    agent_ids = {rec["agent_id"] for rec in r.json()["recommendations"]}
    assert agent_ids == {"AG-1", "AG-2", "AG-3", "AG-4", "AG-5", "AG-6", "AG-8"}


def test_weather_event_only_triggers_assessment_and_situational():
    r = client.post("/ingest/weather", json={
        "location": "Chennai", "temp": 32, "humidity": 85, "wind_speed": 45,
        "lat": 13.08, "lon": 80.27, "alert": "cyclone", "incident_id": "trigger-weather-1",
    })
    assert r.status_code == 200
    agent_ids = {rec["agent_id"] for rec in r.json()["recommendations"]}
    assert agent_ids == {"AG-1", "AG-8"}


def test_satellite_event_triggers_assessment_damage_and_situational():
    r = client.post("/ingest/satellite", json={
        "image_id": "s2-trig-1", "date": "2026-08-13", "cloud_cover": 5,
        "area_bounds": [80.2, 13.0, 80.3, 13.1], "incident_id": "trigger-satellite-1",
    })
    assert r.status_code == 200
    agent_ids = {rec["agent_id"] for rec in r.json()["recommendations"]}
    assert agent_ids == {"AG-1", "AG-2", "AG-8"}
