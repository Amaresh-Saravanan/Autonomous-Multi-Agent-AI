"""Scenario replay test (TDD 7 'Scenario' level, tracker 1.12): replay a
mini escalating-flood dataset through the real HTTP API and assert the
platform's prioritization/severity trend makes sense end to end.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Same sensor, same location, three snapshots of a rising flood.
FLOOD_REPLAY = [
    {"reading": 1.5, "expect_action": "monitor"},
    {"reading": 3.5, "expect_action": "raise_severity"},
    {"reading": 6.0, "expect_action": "raise_severity"},
]
INCIDENT_ID = "scenario-flood-1"
LAT, LON = 13.09, 80.28


def test_escalating_flood_scenario_produces_rising_severity_trend():
    severities = []
    for step in FLOOD_REPLAY:
        r = client.post("/ingest/iot", json={
            "sensor_id": "wl-scn-1", "metric": "water_level",
            "reading": step["reading"], "unit": "m",
            "lat": LAT, "lon": LON, "incident_id": INCIDENT_ID,
        })
        assert r.status_code == 200
        rec = r.json()["recommendations"][0]  # AG-1
        assert rec["action"] == step["expect_action"]
        severities.append(rec["severity"])

    # Prioritization sanity: severity never drops across the escalating replay.
    assert severities == sorted(severities)
    assert severities[-1] == 1.0

    # AG-8 rolling summary reflects the worst-known severity at the end.
    state = client.get(f"/incidents/{INCIDENT_ID}").json()
    assert state["AG-8"]["severity"] == severities[-1]
    assert state["AG-8"]["rationale"].strip()

    # DS-1 severity grid: same location -> one cell, holding the worst case.
    grid = client.get(f"/incidents/{INCIDENT_ID}/severity").json()
    assert len(grid["features"]) == 1
    assert grid["features"][0]["properties"]["severity"] == severities[-1]


if __name__ == "__main__":
    test_escalating_flood_scenario_produces_rising_severity_trend()
    print("OK: escalating flood scenario replay passed.")
