"""E2E self-test for the Phase 0 vertical slice (tracker 0.10).

Proves: synthetic IoT event -> AG-1 -> Recommendation with evidence,
via the real HTTP API, with zero external services.
Run: pytest backend/tests/test_slice.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_normal_reading_does_not_raise_severity():
    r = client.post("/ingest/iot", json={
        "sensor_id": "wl-001", "metric": "water_level",
        "reading": 1.2, "unit": "m", "lat": 13.08, "lon": 80.27,
    })
    assert r.status_code == 200
    rec = r.json()["recommendations"][0]
    assert rec["action"] == "monitor"
    assert rec["severity"] < 0.5


def test_critical_reading_raises_severity_with_evidence():
    r = client.post("/ingest/iot", json={
        "sensor_id": "wl-042", "metric": "water_level",
        "reading": 5.5, "unit": "m", "lat": 13.08, "lon": 80.27,
        "incident_id": "flood-test-1",
    })
    assert r.status_code == 200
    body = r.json()
    rec = body["recommendations"][0]

    assert rec["action"] == "raise_severity"
    assert rec["severity"] == 1.0
    assert rec["evidence"], "recommendation must carry evidence (PRD AC-3)"
    assert rec["rationale"].strip(), "recommendation must carry rationale (PRD DS-7)"
    assert "wl-042" in rec["rationale"]

    # blackboard persisted it
    state = client.get("/incidents/flood-test-1").json()
    assert state["AG-1"]["severity"] == 1.0

    # Phase 2: full 7-agent chain ran and each carries evidence + rationale
    for agent_id in ["AG-1", "AG-2", "AG-3", "AG-4", "AG-5", "AG-6", "AG-8"]:
        assert agent_id in state, f"{agent_id} did not run"
        assert state[agent_id]["evidence"], f"{agent_id} recommendation has no evidence"
        assert state[agent_id]["rationale"].strip(), f"{agent_id} recommendation has no rationale"


if __name__ == "__main__":
    test_health()
    test_normal_reading_does_not_raise_severity()
    test_critical_reading_raises_severity_with_evidence()
    print("OK: Phase 0 vertical slice self-test passed.")
