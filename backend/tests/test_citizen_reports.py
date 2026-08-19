"""Citizen report inbox (PRD UI-4): normalize_citizen already computes a
trust/confidence score per report via citizen_verification.score_confidence,
but nothing persisted it for browsing -- it was thrown away after the ingest
response. This closes that gap: GET /citizen/reports lists what's been ingested.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from fastapi.testclient import TestClient
from app.main import app
from _auth_helpers import viewer_headers

client = TestClient(app)


def test_ingest_citizen_report_is_listed_via_get_citizen_reports():
    incident_id = "citizen-inbox-1"
    r = client.post("/ingest/citizen", json={
        "reporter_id": "citizen-42", "claimed_severity": 0.6,
        "message": "Water rising fast near the bridge",
        "lat": 13.08, "lon": 80.27, "incident_id": incident_id,
    })
    assert r.status_code == 200

    reports = client.get(
        "/citizen/reports", params={"incident_id": incident_id}, headers=viewer_headers()
    ).json()
    assert len(reports) == 1
    report = reports[0]
    assert report["message"] == "Water rising fast near the bridge"
    assert report["reporter_id"] == "citizen-42"
    assert report["incident_id"] == incident_id
    assert "confidence" in report
    assert "flagged_for_review" in report


def test_citizen_reports_endpoint_requires_auth():
    r = client.get("/citizen/reports")
    assert r.status_code == 401
