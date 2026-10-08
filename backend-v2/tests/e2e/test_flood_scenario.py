"""Phase 27: synthetic flood scenario through the real HTTP surface —
authenticated device -> POST ingest -> 202 -> (worker) orchestration ->
recommendations -> human decision -> audit -> alert. The queue worker
normally runs as a background thread (`start_worker_thread`); here we
drive its unit of work directly (`run_for_event`) rather than racing a
real thread against the test, but every other step goes through the
actual API layer, not a shortcut."""

import uuid

import fakeredis
from fastapi.testclient import TestClient

from app.infrastructure.queue import QueueService, get_queue_service
from app.main import app
from app.models.incident import Event
from app.models.resource import Hospital, RescueTeam, Resource, Shelter
from app.models.security import Agency, Device, RoleEnum, User
from app.orchestration.graph import run_for_event
from app.orchestration.state import BlackboardService, get_blackboard_service
from app.security.auth import hash_password


def test_flood_scenario_end_to_end(db):
    agency = Agency(name="City EOC", code="EOC")
    db.add(agency)
    db.commit()

    db.add_all([
        Shelter(name="Shelter", agency_id=agency.id, latitude=13.07, longitude=80.26, capacity=100, occupied=10),
        Hospital(name="Hospital", agency_id=agency.id, latitude=13.05, longitude=80.28, beds_total=50, beds_free=10),
        RescueTeam(name="Team", agency_id=agency.id, latitude=13.06, longitude=80.27),
        Resource(name="Food", category="food_units", agency_id=agency.id, quantity=5000),
        Resource(name="Water", category="water_liters", agency_id=agency.id, quantity=20000),
        Resource(name="Blankets", category="blankets", agency_id=agency.id, quantity=1500),
    ])

    device = Device(device_id="flood-sensor-1", hashed_secret=hash_password("s3cret"), agency_id=agency.id, source_type="iot")
    operator = User(email="ops@eoc.gov", hashed_password=hash_password("pw"), role=RoleEnum.OPERATOR, agency_id=agency.id)
    admin = User(email="admin@eoc.gov", hashed_password=hash_password("pw"), role=RoleEnum.ADMIN, agency_id=agency.id)
    db.add_all([device, operator, admin])
    db.commit()

    client = TestClient(app)
    queue = QueueService("memory")
    blackboard = BlackboardService(fakeredis.FakeStrictRedis(decode_responses=True))
    app.dependency_overrides[get_queue_service] = lambda: queue
    app.dependency_overrides[get_blackboard_service] = lambda: blackboard

    try:
        # 1. authenticated IoT device posts a critical water-level reading
        ingest_resp = client.post(
            "/api/v1/ingestion/iot",
            headers={"X-Device-Id": "flood-sensor-1", "X-Device-Secret": "s3cret"},
            json={"sensor_id": "wl-1", "metric": "water_level", "reading": 5.8, "unit": "m", "lat": 13.07, "lon": 80.26},
        )
        assert ingest_resp.status_code == 202
        event_id = ingest_resp.json()["event_id"]

        event = db.get(Event, uuid.UUID(event_id))
        incident_id = event.incident_id

        # 2. queue -> LangGraph -> AG-1..AG-8 (worker's unit of work, driven directly)
        job = queue.dequeue(timeout=0.1)
        assert job["event_id"] == event_id
        run_for_event(db, uuid.UUID(job["event_id"]), blackboard)

        # 3. operator logs in and sees the generated recommendations
        login = client.post("/api/v1/auth/login", json={"email": "ops@eoc.gov", "password": "pw"})
        token = login.json()["access_token"]
        auth_header = {"Authorization": f"Bearer {token}"}

        recs_resp = client.get(f"/api/v1/recommendations?incident_id={incident_id}", headers=auth_header)
        assert recs_resp.status_code == 200
        recs = recs_resp.json()
        assert len(recs) > 0
        pending = [r for r in recs if r["status"] == "PENDING"]
        assert pending

        # 4. human decision: approve the first pending recommendation
        decide_resp = client.post(
            f"/api/v1/recommendations/{pending[0]['id']}/decide",
            json={"decision": "approve"},
            headers=auth_header,
        )
        assert decide_resp.status_code == 200
        assert decide_resp.json()["status"] == "APPROVED"

        # 5. admin can see the audit trail covering ingestion -> agent runs -> decision
        admin_login = client.post("/api/v1/auth/login", json={"email": "admin@eoc.gov", "password": "pw"})
        admin_header = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        audit_resp = client.get("/api/v1/audit", headers=admin_header)
        assert audit_resp.status_code == 200
        actions = {row["action"] for row in audit_resp.json()}
        assert "recommendation_created" in actions

        # 6. the critical-severity alert was published and is visible to the agency
        alerts_resp = client.get("/api/v1/alerts", headers=auth_header)
        assert alerts_resp.status_code == 200
        assert len(alerts_resp.json()) > 0

        # 7. incident severity reflects AG-1's assessment of the critical reading
        incident_resp = client.get(f"/api/v1/incidents/{incident_id}", headers=auth_header)
        assert incident_resp.json()["severity"] > 0.0
    finally:
        app.dependency_overrides.clear()
