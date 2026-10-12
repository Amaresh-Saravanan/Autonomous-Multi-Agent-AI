import uuid

import fakeredis
from fastapi.testclient import TestClient

from app.infrastructure.queue import QueueService, get_queue_service
from app.main import app
from app.models.incident import Event
from app.models.security import Agency, Device
from app.orchestration.state import BlackboardService, get_blackboard_service
from app.security.auth import hash_password


def _register_device(db, *, source_type="iot"):
    agency = Agency(name="Flood EOC", code="FEOC")
    db.add(agency)
    db.commit()
    device = Device(
        device_id="sensor-1", hashed_secret=hash_password("s3cret"), agency_id=agency.id, source_type=source_type
    )
    db.add(device)
    db.commit()
    return device


def _override_infra():
    queue = QueueService("memory")
    blackboard = BlackboardService(fakeredis.FakeStrictRedis(decode_responses=True))
    app.dependency_overrides[get_queue_service] = lambda: queue
    app.dependency_overrides[get_blackboard_service] = lambda: blackboard
    return queue, blackboard


def test_iot_ingest_returns_202_and_persists_event(db):
    _register_device(db)
    queue, _ = _override_infra()
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/ingestion/iot",
            headers={"X-Device-Id": "sensor-1", "X-Device-Secret": "s3cret"},
            json={"sensor_id": "wl-1", "metric": "water_level", "reading": 4.9, "lat": 13.08, "lon": 80.27},
        )
        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "accepted"

        event = db.get(Event, uuid.UUID(body["event_id"]))
        assert event is not None
        assert event.source_type == "iot"

        job = queue.dequeue(timeout=0.1)
        assert job["event_id"] == body["event_id"]
    finally:
        app.dependency_overrides.clear()


def test_iot_ingest_rejects_device_wrong_source_type(db):
    _register_device(db, source_type="weather")
    _override_infra()
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/ingestion/iot",
            headers={"X-Device-Id": "sensor-1", "X-Device-Secret": "s3cret"},
            json={"sensor_id": "wl-1", "reading": 4.9, "lat": 13.08, "lon": 80.27},
        )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_iot_ingest_without_device_headers_rejected(db):
    _override_infra()
    try:
        client = TestClient(app)
        resp = client.post(
            "/api/v1/ingestion/iot",
            json={"sensor_id": "wl-1", "reading": 4.9, "lat": 13.08, "lon": 80.27},
        )
        assert resp.status_code == 422  # missing required header
    finally:
        app.dependency_overrides.clear()
