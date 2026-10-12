"""Endpoints the operations console depends on (PRD UI-1..UI-12)."""

import uuid
from datetime import datetime, timezone

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.audit import AuditLog
from app.models.citizen import CitizenReport
from app.models.incident import Event, Incident, LocationStateEnum
from app.models.recommendation import Recommendation
from app.models.security import Agency, RoleEnum, User
from app.orchestration.state import BlackboardService, get_blackboard_service
from app.security.auth import hash_password


@pytest.fixture(autouse=True)
def _fake_blackboard():
    board = BlackboardService(fakeredis.FakeRedis(decode_responses=True))
    app.dependency_overrides[get_blackboard_service] = lambda: board
    yield board
    app.dependency_overrides.pop(get_blackboard_service, None)


def _login(client, db, role=RoleEnum.ADMIN, email="admin@eoc.gov"):
    agency = db.query(Agency).first() or Agency(name="City EOC", code="EOC1")
    db.add(agency)
    db.commit()
    db.add(User(email=email, hashed_password=hash_password("pw-123456"), role=role, agency_id=agency.id))
    db.commit()
    body = client.post("/api/v1/auth/login", json={"email": email, "password": "pw-123456"}).json()
    return {"Authorization": f"Bearer {body['access_token']}"}, agency, body


def _incident(db, severity=0.9):
    inc = Incident(severity=severity, location_state=LocationStateEnum.EXACT, latitude=13.08, longitude=80.27)
    db.add(inc)
    db.commit()
    db.add(Event(incident_id=inc.id, source_type="iot", payload={}, location_state=LocationStateEnum.EXACT,
                 latitude=13.08, longitude=80.27, received_at=datetime.now(timezone.utc)))
    db.commit()
    return inc


def test_login_returns_agency_name_and_me_endpoint(db):
    client = TestClient(app)
    headers, agency, body = _login(client, db)
    assert body["agency_name"] == "City EOC" and body["email"] == "admin@eoc.gov"
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["role"] == "ADMIN" and me["email"] == "admin@eoc.gov"
    assert client.get("/api/v1/auth/me").status_code == 401


def test_recommendation_response_carries_console_fields_and_decision_is_audited(db):
    client = TestClient(app)
    headers, agency, _ = _login(client, db)
    inc = _incident(db)
    rec = Recommendation(
        incident_id=inc.id, agent_id="AG-6", action="route:s1", priority="high", confidence=0.7,
        reasoning="clear route", severity=0.9, evidence_json=["evt-1"],
        details_json={"destination": {"id": "s1", "lat": 13.1, "lon": 80.3}, "blocked": False},
        target_agency_id=agency.id,
    )
    db.add(rec)
    db.commit()

    item = client.get("/api/v1/recommendations", headers=headers).json()[0]
    assert item["severity"] == 0.9 and item["evidence"] == ["evt-1"]
    assert item["geo"] == {"type": "Point", "coordinates": [80.27, 13.08]}
    assert item["details"]["route_line"] == [[80.27, 13.08], [80.3, 13.1]]

    resp = client.post(f"/api/v1/recommendations/{rec.id}/decide", headers=headers, json={"decision": "approve"})
    assert resp.status_code == 200 and resp.json()["status"] == "APPROVED"
    log = db.query(AuditLog).filter(AuditLog.action == "recommendation_approve").one()
    assert log.actor_id == "admin@eoc.gov" and log.recommendation_id == rec.id


def test_incident_list_state_and_severity(db, _fake_blackboard):
    client = TestClient(app)
    headers, *_ = _login(client, db)
    inc = _incident(db, severity=0.8)

    listing = client.get("/api/v1/incidents", headers=headers).json()
    assert listing[0]["event_count"] == 1

    bb = _fake_blackboard
    bb.merge(str(inc.id), "AG-5", {"severity": 0.8, "details": {"shelter": {"id": "A"}}})
    bb.merge(str(inc.id), "AG-6", {"severity": 0.8, "details": {"destination": {"id": "B"}}})
    state = client.get(f"/api/v1/incidents/{inc.id}/state", headers=headers).json()
    assert "AG-5" in state and state["conflicts"][0]["agents"] == ["AG-5", "AG-6"]

    geo = client.get(f"/api/v1/incidents/{inc.id}/severity", headers=headers).json()
    assert geo["type"] == "FeatureCollection" and len(geo["features"]) == 1
    assert geo["features"][0]["properties"]["severity"] == 0.8

    assert client.get(f"/api/v1/incidents/{uuid.uuid4()}/state", headers=headers).status_code == 404


def test_citizen_reports_mask_contact_for_viewers(db):
    client = TestClient(app)
    admin_headers, agency, _ = _login(client, db)
    inc = _incident(db)
    db.add(CitizenReport(incident_id=inc.id, reporter_contact="+91-9000000000", message="water rising",
                         verification_score=0.2, claimed_severity=0.9, flagged_for_review=True))
    db.commit()
    viewer_headers, _, _ = _login(client, db, role=RoleEnum.VIEWER, email="viewer@eoc.gov")

    admin_view = client.get("/api/v1/citizen/reports", headers=admin_headers).json()[0]
    viewer_view = client.get("/api/v1/citizen/reports", headers=viewer_headers).json()[0]
    assert admin_view["reporter_id"] == "+91-9000000000" and admin_view["flagged_for_review"] is True
    assert viewer_view["reporter_id"] == "hidden"
    assert client.get("/api/v1/citizen/reports").status_code == 401


def test_metrics_summary_and_agent_health_require_roles(db):
    client = TestClient(app)
    viewer_headers, *_ = _login(client, db, role=RoleEnum.VIEWER, email="v@eoc.gov")
    assert client.get("/api/v1/metrics", headers=viewer_headers).status_code == 403
    assert client.get("/api/v1/agents/health", headers=viewer_headers).status_code == 200
    op_headers, *_ = _login(client, db, role=RoleEnum.OPERATOR, email="o@eoc.gov")
    body = client.get("/api/v1/metrics", headers=op_headers).json()
    assert "routes" in body and "recommendation_acceptance_rate" in body


def test_forecast_projects_rising_water_and_refuses_thin_data(db):
    from datetime import timedelta

    client = TestClient(app)
    headers, *_ = _login(client, db)
    inc = _incident(db)
    base = datetime.now(timezone.utc) - timedelta(hours=2)
    assert client.get(f"/api/v1/incidents/{inc.id}/forecast", headers=headers).json()["status"] == "insufficient_data"

    for i, level in enumerate([2.0, 2.5, 3.0, 3.5, 4.0]):  # +1.0 m/h
        db.add(Event(incident_id=inc.id, source_type="iot", location_state=LocationStateEnum.EXACT,
                     latitude=13.08, longitude=80.27, received_at=base + timedelta(minutes=30 * i),
                     payload={"sensor_id": "s1", "metric": "water_level", "reading": level, "unit": "m"}))
    db.commit()
    f = client.get(f"/api/v1/incidents/{inc.id}/forecast", headers=headers).json()
    assert f["status"] == "ok" and f["trend"] == "rising"
    assert abs(f["slope_per_hour"] - 1.0) < 0.01 and f["fit_r2"] == 1.0
    assert [h["hours"] for h in f["horizons"]] == [1, 3, 6]
    assert f["horizons"][0]["predicted_value"] == 5.0 and f["horizons"][0]["predicted_severity"] == 1.0
    assert "heuristic" in f["method"] and f["disclaimer"]
    assert client.get(f"/api/v1/incidents/{inc.id}/forecast").status_code == 401
