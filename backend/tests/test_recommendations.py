"""Human approve/reject on recommendations (tracker 2.9, PRD AC-5) — audited."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from fastapi.testclient import TestClient
from app.main import app
from app import audit

client = TestClient(app)


def _make_pending_rec():
    r = client.post("/ingest/iot", json={
        "sensor_id": "wl-approve-1", "metric": "water_level",
        "reading": 3.5, "unit": "m", "lat": 13.0, "lon": 80.0,
        "incident_id": "approve-test-1",
    })
    return r.json()["recommendations"][0]  # AG-1, status="pending"


def test_pending_recommendation_is_listed():
    rec = _make_pending_rec()
    pending = client.get("/recommendations?status=pending").json()
    assert any(r["rec_id"] == rec["rec_id"] for r in pending)


def test_approve_flips_status_and_writes_audit_entry():
    rec = _make_pending_rec()
    before_audit_len = len(audit.all_entries())

    r = client.post(f"/recommendations/{rec['rec_id']}/approve")
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    # No longer pending.
    pending = client.get("/recommendations?status=pending").json()
    assert not any(x["rec_id"] == rec["rec_id"] for x in pending)

    # Blackboard reflects the decision (frontend "why" panel reads from here).
    state = client.get(f"/incidents/{rec['incident_id']}").json()
    assert state[rec["agent_id"]]["status"] == "approved"

    # Audited.
    entries = audit.all_entries()
    assert len(entries) == before_audit_len + 1
    assert entries[-1]["action"] == "approved"
    assert entries[-1]["target"] == rec["rec_id"]
    assert entries[-1]["before"]["status"] == "pending"
    assert entries[-1]["after"]["status"] == "approved"


def test_audit_entries_are_immutable_once_written():
    rec = _make_pending_rec()
    client.post(f"/recommendations/{rec['rec_id']}/approve")
    client.post(f"/recommendations/{rec['rec_id']}/reject")

    entries = [e for e in audit.all_entries() if e["target"] == rec["rec_id"]]
    assert len(entries) == 2
    assert entries[0]["action"] == "approved"
    assert entries[0]["after"]["status"] == "approved"  # must not become "rejected"
    assert entries[1]["action"] == "rejected"


def test_reject_flips_status():
    rec = _make_pending_rec()
    r = client.post(f"/recommendations/{rec['rec_id']}/reject")
    assert r.json()["status"] == "rejected"


def test_unknown_recommendation_is_404():
    r = client.post("/recommendations/does-not-exist/approve")
    assert r.status_code == 404


if __name__ == "__main__":
    test_pending_recommendation_is_listed()
    test_approve_flips_status_and_writes_audit_entry()
    test_audit_entries_are_immutable_once_written()
    test_reject_flips_status()
    test_unknown_recommendation_is_404()
    print("OK: recommendation approve/reject + audit tests passed.")
