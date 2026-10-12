"""Signup / password-reset requests -> admin approval -> forced password change."""

from fastapi.testclient import TestClient

from app.main import app
from app.models.access import AccessRequest
from app.models.audit import AuditLog
from app.models.security import Agency, Device, RoleEnum, User
from app.security.auth import hash_password

from tests.integration.test_console_api import _login

DEV = {"X-Device-Id": "cit-1", "X-Device-Secret": "cs3cret"}


def _citizen_device(db):
    agency = db.query(Agency).first() or Agency(name="City EOC", code="EOC1")
    db.add(agency)
    db.commit()
    db.add(Device(device_id="cit-1", hashed_secret=hash_password("cs3cret"), agency_id=agency.id, source_type="citizen"))
    db.commit()


def test_public_endpoints_need_device_credentials_and_are_generic(db):
    client = TestClient(app)
    body = {"email": "new@x.org", "full_name": "New Person"}
    assert client.post("/api/v1/access/request", json=body).status_code == 422  # no device headers
    _citizen_device(db)
    a = client.post("/api/v1/access/request", json=body, headers=DEV)
    b = client.post("/api/v1/access/request", json=body, headers=DEV)  # duplicate
    assert a.status_code == b.status_code == 202 and a.json() == b.json()
    assert db.query(AccessRequest).count() == 1

    # Reset for an unknown email: same acknowledgement, nothing stored.
    r = client.post("/api/v1/access/reset-request", json={"email": "ghost@x.org"}, headers=DEV)
    assert r.status_code == 202 and r.json() == a.json()
    assert db.query(AccessRequest).count() == 1


def test_cannot_self_request_admin_and_existing_email_is_not_queued(db):
    client = TestClient(app)
    _citizen_device(db)
    client.post("/api/v1/access/request", headers=DEV,
                json={"email": "x@x.org", "full_name": "Xx", "requested_role": "ADMIN"})
    assert db.query(AccessRequest).one().requested_role is None
    admin_h, agency, _ = _login(client, db)
    client.post("/api/v1/access/request", headers=DEV, json={"email": "ADMIN@eoc.gov", "full_name": "Dup"})
    assert db.query(AccessRequest).count() == 1


def test_admin_approves_signup_new_user_must_change_password(db):
    client = TestClient(app)
    _citizen_device(db)
    admin_h, agency, _ = _login(client, db)
    client.post("/api/v1/access/request", headers=DEV,
                json={"email": "Op@Example.org", "full_name": "Pat Op", "requested_role": "OPERATOR"})
    req = client.get("/api/v1/access/requests?status=PENDING", headers=admin_h).json()[0]
    assert req["email"] == "op@example.org" and req["requested_role"] == "OPERATOR"
    assert client.get("/api/v1/access/agencies", headers=admin_h).json()[0]["id"] == str(agency.id)

    assert client.post(f"/api/v1/access/requests/{req['id']}/approve", headers=admin_h, json={}).status_code == 422  # no agency
    ok = client.post(f"/api/v1/access/requests/{req['id']}/approve", headers=admin_h, json={"agency_id": str(agency.id)})
    temp = ok.json()["temporary_password"]
    assert ok.status_code == 200 and len(temp) >= 12
    assert client.post(f"/api/v1/access/requests/{req['id']}/approve", headers=admin_h, json={}).status_code == 422  # already decided

    login = client.post("/api/v1/auth/login", json={"email": "OP@example.org", "password": temp}).json()
    assert login["must_change_password"] is True and login["role"] == "OPERATOR"
    h = {"Authorization": f"Bearer {login['access_token']}"}
    assert client.get("/api/v1/incidents", headers=h).status_code == 403  # blocked until changed
    assert client.get("/api/v1/auth/me", headers=h).json()["must_change_password"] is True

    assert client.post("/api/v1/auth/change-password", headers=h,
                       json={"current_password": "wrong", "new_password": "a-new-strong-pass"}).status_code == 401
    assert client.post("/api/v1/auth/change-password", headers=h,
                       json={"current_password": temp, "new_password": "short"}).status_code == 422
    assert client.post("/api/v1/auth/change-password", headers=h,
                       json={"current_password": temp, "new_password": "a-new-strong-pass"}).status_code == 204
    assert client.get("/api/v1/incidents", headers=h).status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": "op@example.org", "password": temp}).status_code == 401
    actions = {a.action for a in db.query(AuditLog).all()}
    assert {"access_signup_approved", "password_changed"} <= actions


def test_reset_flow_and_reject_and_role_gate(db):
    client = TestClient(app)
    _citizen_device(db)
    admin_h, agency, _ = _login(client, db)
    db.add(User(email="v@eoc.gov", hashed_password=hash_password("old-password-1"), role=RoleEnum.VIEWER, agency_id=agency.id))
    db.commit()
    client.post("/api/v1/access/reset-request", headers=DEV, json={"email": "v@eoc.gov"})
    req = client.get("/api/v1/access/requests", headers=admin_h).json()[0]
    assert req["kind"] == "RESET"
    temp = client.post(f"/api/v1/access/requests/{req['id']}/approve", headers=admin_h, json={}).json()["temporary_password"]
    assert client.post("/api/v1/auth/login", json={"email": "v@eoc.gov", "password": "old-password-1"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "v@eoc.gov", "password": temp}).json()["must_change_password"]

    # Non-admins cannot see or decide requests.
    op_h, *_ = _login(client, db, RoleEnum.OPERATOR, "op@eoc.gov")
    assert client.get("/api/v1/access/requests", headers=op_h).status_code == 403
    client.post("/api/v1/access/request", headers=DEV, json={"email": "rej@x.org", "full_name": "Rej Ected"})
    rid = [r for r in client.get("/api/v1/access/requests?status=PENDING", headers=admin_h).json()][0]["id"]
    assert client.post(f"/api/v1/access/requests/{rid}/reject", headers=admin_h).json()["status"] == "REJECTED"
    assert db.query(User).filter(User.email == "rej@x.org").count() == 0
