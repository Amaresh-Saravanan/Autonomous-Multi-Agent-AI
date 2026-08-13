"""RBAC: JWT auth + in-memory users (tracker 3.4). Unit tests on app/auth.py
directly, then integration tests gating real routes via TestClient.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

import jwt
import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app

client = TestClient(app)


# ---- unit: password hashing ----

def test_password_hash_round_trip():
    salt = auth.new_salt()
    hashed = auth.hash_password("correct-horse", salt)
    assert auth.verify_password("correct-horse", salt, hashed)


def test_password_hash_rejects_wrong_password():
    salt = auth.new_salt()
    hashed = auth.hash_password("correct-horse", salt)
    assert not auth.verify_password("wrong-password", salt, hashed)


# ---- unit: JWT issue/verify ----

def test_issue_and_verify_token_round_trip():
    token = auth.issue_token("alice_admin", "admin", "city_emergency_mgmt")
    payload = auth.verify_token(token)
    assert payload["username"] == "alice_admin"
    assert payload["role"] == "admin"
    assert payload["agency"] == "city_emergency_mgmt"


def test_tampered_token_fails_verification():
    token = auth.issue_token("alice_admin", "admin", "city_emergency_mgmt")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(jwt.InvalidTokenError):
        auth.verify_token(tampered)


def test_expired_token_fails_verification():
    expired = jwt.encode(
        {"username": "bob_operator", "role": "operator", "agency": "city_emergency_mgmt",
         "exp": time.time() - 10},
        auth.JWT_SECRET, algorithm="HS256",
    )
    with pytest.raises(jwt.InvalidTokenError):
        auth.verify_token(expired)


# ---- integration: /auth/login ----

def test_login_with_valid_credentials_returns_token():
    r = client.post("/auth/login", json={"username": "alice_admin", "password": "admin-pass"})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_with_wrong_password_is_401():
    r = client.post("/auth/login", json={"username": "alice_admin", "password": "nope"})
    assert r.status_code == 401


def test_login_with_unknown_user_is_401():
    r = client.post("/auth/login", json={"username": "nobody", "password": "x"})
    assert r.status_code == 401


def _token_for(username: str, password: str) -> str:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


def _auth_header(username: str, password: str) -> dict:
    return {"Authorization": f"Bearer {_token_for(username, password)}"}


def _make_pending_rec():
    r = client.post("/ingest/iot", json={
        "sensor_id": "wl-auth-1", "metric": "water_level",
        "reading": 3.5, "unit": "m", "lat": 13.0, "lon": 80.0,
        "incident_id": "auth-test-1",
    })
    return r.json()["recommendations"][0]


def test_operator_token_can_approve():
    rec = _make_pending_rec()
    r = client.post(
        f"/recommendations/{rec['rec_id']}/approve",
        headers=_auth_header("bob_operator", "operator-pass"),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "approved"


def test_admin_token_can_approve():
    """admin implicitly satisfies operator+ role checks."""
    rec = _make_pending_rec()
    r = client.post(
        f"/recommendations/{rec['rec_id']}/approve",
        headers=_auth_header("alice_admin", "admin-pass"),
    )
    assert r.status_code == 200


def test_viewer_token_cannot_approve():
    rec = _make_pending_rec()
    r = client.post(
        f"/recommendations/{rec['rec_id']}/approve",
        headers=_auth_header("carol_viewer", "viewer-pass"),
    )
    assert r.status_code == 403


def test_no_token_on_approve_is_401():
    rec = _make_pending_rec()
    r = client.post(f"/recommendations/{rec['rec_id']}/approve")
    assert r.status_code == 401


def test_no_token_on_reject_is_401():
    rec = _make_pending_rec()
    r = client.post(f"/recommendations/{rec['rec_id']}/reject")
    assert r.status_code == 401


if __name__ == "__main__":
    test_password_hash_round_trip()
    test_password_hash_rejects_wrong_password()
    test_issue_and_verify_token_round_trip()
    test_tampered_token_fails_verification()
    test_expired_token_fails_verification()
    test_login_with_valid_credentials_returns_token()
    test_login_with_wrong_password_is_401()
    test_login_with_unknown_user_is_401()
    test_operator_token_can_approve()
    test_admin_token_can_approve()
    test_viewer_token_cannot_approve()
    test_no_token_on_approve_is_401()
    test_no_token_on_reject_is_401()
    print("OK: RBAC auth tests passed.")
