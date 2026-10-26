"""Phase 28: with QUEUE_BACKEND=memory and no real Redis running, the whole
pipeline (queue -> background worker -> blackboard -> pubsub) must still
work via the shared fakeredis singleton (app/infrastructure/redis.py).
Unlike the other ingestion/orchestration tests, this one deliberately does
NOT override get_queue_service/get_blackboard_service -- it drives the real
background worker thread (`start_worker_thread`, started by the app's
lifespan) to prove the fix, not a manually-invoked `run_for_event`.

backend-v2/.env (real dev config) sets QUEUE_BACKEND=redis against a real
Upstash instance, and get_settings/get_redis_client/get_queue_service are
all `@lru_cache`d -- so this test must explicitly force the memory setting
and clear those caches, same as the `QUEUE_BACKEND=memory` opt-in the fix
itself requires (never an implicit fallback)."""

import time

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.infrastructure.queue import get_queue_service
from app.infrastructure.redis import get_redis_client
from app.main import app
from app.models.resource import Hospital, RescueTeam, Resource, Shelter
from app.models.security import Agency, Device, RoleEnum, User
from app.security.auth import hash_password


@pytest.fixture
def memory_backend(monkeypatch):
    monkeypatch.setenv("QUEUE_BACKEND", "memory")
    get_settings.cache_clear()
    get_redis_client.cache_clear()
    get_queue_service.cache_clear()
    yield
    get_settings.cache_clear()
    get_redis_client.cache_clear()
    get_queue_service.cache_clear()


def test_pipeline_runs_end_to_end_with_memory_backend_and_no_redis(db, memory_backend):
    agency = Agency(name="City EOC", code="EOC-MEM")
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
    device = Device(device_id="mem-sensor-1", hashed_secret=hash_password("s3cret"), agency_id=agency.id, source_type="iot")
    operator = User(email="ops@mem-eoc.gov", hashed_password=hash_password("pw"), role=RoleEnum.OPERATOR, agency_id=agency.id)
    db.add_all([device, operator])
    db.commit()

    # `with` triggers the app's lifespan, which starts the real background
    # worker thread against the real (fakeredis-backed) queue/blackboard --
    # no dependency override, so this exercises the actual no-Redis path.
    with TestClient(app) as client:
        ingest_resp = client.post(
            "/api/v1/ingestion/iot",
            headers={"X-Device-Id": "mem-sensor-1", "X-Device-Secret": "s3cret"},
            json={"sensor_id": "wl-mem-1", "metric": "water_level", "reading": 5.8, "unit": "m", "lat": 13.07, "lon": 80.26},
        )
        assert ingest_resp.status_code == 202
        incident_id = ingest_resp.json()["incident_id"]

        login = client.post("/api/v1/auth/login", json={"email": "ops@mem-eoc.gov", "password": "pw"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # Wait for the whole chain, not just the first agent: AG-8 is always
        # last (`AGENT_CHAIN`), so its presence means the worker fully
        # drained this job. Breaking out early (on just *any* recommendation)
        # would let the test -- and the session-scoped schema teardown --
        # race the still-running worker thread for the later agents.
        recs = []
        for _ in range(50):
            recs = client.get(f"/api/v1/recommendations?incident_id={incident_id}", headers=headers).json()
            if any(r["agent_id"] == "AG-8" for r in recs):
                break
            time.sleep(0.2)

        assert recs, "worker never processed the queued job against the fakeredis blackboard"
        assert any(r["agent_id"] == "AG-8" for r in recs), "worker never finished the full agent chain"
        for rec in recs:
            assert rec["evidence"], f"{rec['agent_id']} recommendation has empty evidence"
            assert rec["reasoning"], f"{rec['agent_id']} recommendation has empty reasoning"

        alerts = client.get("/api/v1/alerts", headers=headers).json()
        assert alerts, "no alert was published over the fakeredis pubsub channel"
