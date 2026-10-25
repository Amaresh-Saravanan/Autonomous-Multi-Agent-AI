"""Admin-only /poll/* endpoint tests. The runner itself (real poll logic)
is covered in test_poller_runner.py -- here get_default_runner is swapped
for a fake so these only exercise routing, auth, and response shape."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api import ingestion as ingestion_module
from app.ingestion.pollers.results import PollResult
from app.ingestion.pollers.status import StatusStore
from app.main import app
from app.models.security import Agency, RoleEnum, User
from app.security.auth import hash_password


def _login(client, db, role, email):
    agency = Agency(name="EOC", code="EOC-POLL")
    db.add(agency)
    db.commit()
    db.add(User(email=email, hashed_password=hash_password("pw-123456"), role=role, agency_id=agency.id))
    db.commit()
    body = client.post("/api/v1/auth/login", json={"email": email, "password": "pw-123456"}).json()
    return {"Authorization": f"Bearer {body['access_token']}"}


class _FakeRunner:
    def __init__(self):
        self.status = StatusStore()
        self.status.record_success("usgs", count=3, run_at=datetime.now(timezone.utc))
        self.calls = []

    def run_once(self, source):
        self.calls.append(source)
        return PollResult(fetched=1, ingested=1, skipped_duplicate=0, error=None)


@pytest.fixture
def fake_runner(monkeypatch):
    runner = _FakeRunner()
    monkeypatch.setattr(ingestion_module, "get_default_runner", lambda: runner)
    return runner


def test_trigger_poll_requires_admin(db, fake_runner):
    client = TestClient(app)
    headers = _login(client, db, RoleEnum.VIEWER, "viewer@eoc.gov")

    resp = client.post("/api/v1/ingestion/poll/usgs", headers=headers)

    assert resp.status_code == 403
    assert fake_runner.calls == []


def test_trigger_poll_runs_source_and_returns_result(db, fake_runner):
    client = TestClient(app)
    headers = _login(client, db, RoleEnum.ADMIN, "admin@eoc.gov")

    resp = client.post("/api/v1/ingestion/poll/usgs", headers=headers)

    assert resp.status_code == 200
    assert resp.json() == {"fetched": 1, "ingested": 1, "skipped_duplicate": 0, "error": None}
    assert fake_runner.calls == ["usgs"]


def test_trigger_poll_rejects_unknown_source(db, fake_runner):
    client = TestClient(app)
    headers = _login(client, db, RoleEnum.ADMIN, "admin@eoc.gov")

    resp = client.post("/api/v1/ingestion/poll/not-a-real-source", headers=headers)

    assert resp.status_code == 400
    assert fake_runner.calls == []


def test_poll_status_returns_per_source_shape(db, fake_runner):
    client = TestClient(app)
    headers = _login(client, db, RoleEnum.ADMIN, "admin@eoc.gov")

    resp = client.get("/api/v1/ingestion/poll/status", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["usgs"]["last_count"] == 3
    assert body["usgs"]["last_error"] is None
    assert body["usgs"]["last_run"] is not None


def test_poll_status_requires_admin(db, fake_runner):
    client = TestClient(app)
    headers = _login(client, db, RoleEnum.OPERATOR, "operator@eoc.gov")

    resp = client.get("/api/v1/ingestion/poll/status", headers=headers)

    assert resp.status_code == 403
