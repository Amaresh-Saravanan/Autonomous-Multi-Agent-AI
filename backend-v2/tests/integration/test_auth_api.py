from fastapi.testclient import TestClient

from app.main import app
from app.models.security import Agency, RoleEnum, User
from app.security.auth import hash_password


def test_login_returns_token_for_valid_credentials(db):
    agency = Agency(name="City EOC", code="EOC1")
    db.add(agency)
    db.commit()
    db.add(
        User(
            email="operator@eoc.gov",
            hashed_password=hash_password("strong-pass"),
            role=RoleEnum.OPERATOR,
            agency_id=agency.id,
        )
    )
    db.commit()

    client = TestClient(app)
    resp = client.post("/api/v1/auth/login", json={"email": "operator@eoc.gov", "password": "strong-pass"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "OPERATOR"
    assert body["access_token"]


def test_login_wrong_password_returns_structured_401():
    client = TestClient(app)
    resp = client.post("/api/v1/auth/login", json={"email": "nobody@eoc.gov", "password": "x"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"] == "authentication_error"
    assert "message" in body
