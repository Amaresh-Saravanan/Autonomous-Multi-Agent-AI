"""Audit log wired to all state changes (tracker 1.11) — beyond approve/reject
(2.9), every blackboard write the orchestrator makes (agent recommendations,
conflict detection) must also produce an audit entry, actor="system" since
no human is involved.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from fastapi.testclient import TestClient
from app.main import app
from app import audit

client = TestClient(app)


def test_ingest_records_an_audit_entry_per_agent_recommendation():
    incident_id = "audit-coverage-1"
    r = client.post("/ingest/iot", json={
        "sensor_id": "wl-audit-1", "metric": "water_level", "reading": 5.5,
        "unit": "m", "lat": 13.05, "lon": 80.25, "incident_id": incident_id,
    })
    assert r.status_code == 200
    recs = r.json()["recommendations"]

    entries = [e for e in audit.all_entries() if e["target"].startswith(f"{incident_id}:")]
    assert len(entries) == len(recs)
    assert all(e["actor"] == "system" for e in entries)
    assert all(e["action"] == "agent_recommendation" for e in entries)
    agent_ids = {e["target"].split(":", 1)[1] for e in entries}
    assert "AG-1" in agent_ids  # AG-1 always runs (triggers on every source_type)


def test_conflict_detection_records_an_audit_entry():
    incident_id = "audit-coverage-conflict-1"
    r = client.post("/ingest/iot", json={
        "sensor_id": "wl-audit-conflict-1", "metric": "water_level",
        "reading": 6.0, "unit": "m",
        "lat": 13.07, "lon": 80.26,  # s-1's own coords: unambiguously nearest, seeded full
        "incident_id": incident_id,
    })
    assert r.status_code == 200

    entries = [
        e for e in audit.all_entries()
        if e["target"] == incident_id and e["action"] == "conflict_detected"
    ]
    assert len(entries) == 1
    assert entries[0]["actor"] == "system"
    assert len(entries[0]["after"]["conflicts"]) == 1
