"""Citizen report ingestion + trust/verification (tracker 3.3, SEC-4).

A citizen report is scored for trust against AG-1's current severity but
does NOT wake any orchestrator agent (see
docs/superpowers/specs/2026-08-13-citizen-verification-design.md).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from fastapi.testclient import TestClient
from app.main import app
from app import blackboard
from app.normalizers import normalize_citizen

client = TestClient(app)


def _raw(incident_id, claimed_severity=0.5):
    return {
        "reporter_id": "citizen-1",
        "claimed_severity": claimed_severity,
        "message": "water rising fast near the bridge",
        "lat": 13.08,
        "lon": 80.27,
        "incident_id": incident_id,
    }


def test_normalize_citizen_returns_citizen_event():
    event = normalize_citizen(_raw("citizen-basic-1"))
    assert event.source_type == "citizen"


def test_corroborating_claim_gets_high_confidence():
    blackboard.merge("citizen-corrob-1", {"AG-1": {"severity": 0.6}})
    event = normalize_citizen(_raw("citizen-corrob-1", claimed_severity=0.65))
    assert event.confidence >= 0.7


def test_divergent_claim_gets_low_confidence_and_flagged():
    blackboard.merge("citizen-diverge-1", {"AG-1": {"severity": 0.6}})
    event = normalize_citizen(_raw("citizen-diverge-1", claimed_severity=0.1))
    assert event.confidence <= 0.3
    assert event.payload.get("flagged_for_review") is True


def test_no_prior_state_gets_neutral_confidence_not_flagged():
    event = normalize_citizen(_raw("citizen-fresh-1", claimed_severity=0.5))
    assert 0.3 < event.confidence < 0.7
    assert not event.payload.get("flagged_for_review")


def test_ingest_citizen_endpoint_succeeds_and_wakes_no_agent():
    r = client.post("/ingest/citizen", json=_raw("citizen-endpoint-1"))
    assert r.status_code == 200
    assert r.json()["recommendations"] == []
