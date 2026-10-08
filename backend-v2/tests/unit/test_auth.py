import pytest

from app.errors import AuthenticationError
from app.models.security import Agency, RoleEnum, User
from app.security.auth import authenticate_user, hash_password, verify_password
from app.security.jwt import create_access_token, decode_access_token


def test_password_hash_round_trips():
    hashed = hash_password("correct-horse")
    assert verify_password("correct-horse", hashed)
    assert not verify_password("wrong", hashed)


def test_authenticate_user_success_and_failure(db):
    agency = Agency(name="A", code="A1")
    db.add(agency)
    db.commit()
    user = User(email="a@b.com", hashed_password=hash_password("pw123"), role=RoleEnum.VIEWER, agency_id=agency.id)
    db.add(user)
    db.commit()

    found = authenticate_user(db, "a@b.com", "pw123")
    assert found.id == user.id

    with pytest.raises(AuthenticationError):
        authenticate_user(db, "a@b.com", "wrong-password")

    with pytest.raises(AuthenticationError):
        authenticate_user(db, "nobody@b.com", "pw123")


def test_jwt_round_trip_and_rejects_tampering():
    token = create_access_token(subject="user-1", role="VIEWER", agency_id="agency-1")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-1"
    assert payload["role"] == "VIEWER"

    with pytest.raises(AuthenticationError):
        decode_access_token(token + "tampered")
