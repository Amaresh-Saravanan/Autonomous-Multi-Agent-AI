"""GET /incidents (BE-1) and GET /audit (BE-2) — tracker 3.11.6.2 / 3.11.6.10.

Both endpoints already had their data available in-process (incidents
registry, audit log); this only proves the new routes expose it correctly,
with the right role gates.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from fastapi.testclient import TestClient
from app.main import app
from _auth_helpers import admin_headers, operator_headers, viewer_headers

client = TestClient(app)


def _ingest(incident_id: str, lat: float = 13.0, lon: float = 80.0):
    return client.post("/ingest/iot", json={
        "sensor_id": "wl-list-1", "metric": "water_level",
        "reading": 3.5, "unit": "m", "lat": lat, "lon": lon,
        "incident_id": incident_id,
    })


def test_list_incidents_includes_a_just_ingested_incident():
    _ingest("incidents-list-test-1")
    seen = client.get("/incidents", headers=viewer_headers()).json()
    assert any(i["incident_id"] == "incidents-list-test-1" for i in seen)


def test_list_incidents_newest_activity_first():
    _ingest("incidents-list-test-old")
    _ingest("incidents-list-test-new")
    seen = client.get("/incidents", headers=viewer_headers()).json()
    ids = [i["incident_id"] for i in seen]
    assert ids.index("incidents-list-test-new") < ids.index("incidents-list-test-old")


def test_list_incidents_requires_auth():
    r = client.get("/incidents")
    assert r.status_code == 401


def test_audit_requires_admin():
    r = client.get("/audit", headers=operator_headers())
    assert r.status_code == 403


def test_audit_admin_sees_entries():
    rec = _ingest("audit-route-test-1").json()["recommendations"][0]
    client.post(f"/recommendations/{rec['rec_id']}/approve", headers=operator_headers())

    entries = client.get("/audit", headers=admin_headers()).json()
    assert any(e["target"] == rec["rec_id"] and e["action"] == "approved" for e in entries)


if __name__ == "__main__":
    test_list_incidents_includes_a_just_ingested_incident()
    test_list_incidents_newest_activity_first()
    test_list_incidents_requires_auth()
    test_audit_requires_admin()
    test_audit_admin_sees_entries()
    print("OK: GET /incidents + GET /audit route tests passed.")
