import pytest

from app.errors import AuthenticationError, AuthorizationError
from app.models.security import Agency, Device, DeviceStatusEnum
from app.security.auth import hash_password
from app.security.devices import authenticate_device


def _make_device(db, *, source_type="iot", status=DeviceStatusEnum.ACTIVE):
    agency = Agency(name="Flood Response", code="FR1")
    db.add(agency)
    db.commit()
    device = Device(
        device_id="sensor-42",
        hashed_secret=hash_password("s3cret"),
        agency_id=agency.id,
        source_type=source_type,
        status=status,
    )
    db.add(device)
    db.commit()
    return device


def test_authenticate_device_success(db):
    _make_device(db)
    device = authenticate_device(db, "sensor-42", "s3cret", "iot")
    assert device.device_id == "sensor-42"
    assert device.last_seen_at is not None


def test_authenticate_device_wrong_secret(db):
    _make_device(db)
    with pytest.raises(AuthenticationError):
        authenticate_device(db, "sensor-42", "wrong", "iot")


def test_authenticate_device_wrong_source_type_rejected(db):
    _make_device(db, source_type="iot")
    with pytest.raises(AuthorizationError):
        authenticate_device(db, "sensor-42", "s3cret", "weather")


def test_revoked_device_rejected(db):
    _make_device(db, status=DeviceStatusEnum.REVOKED)
    with pytest.raises(AuthenticationError):
        authenticate_device(db, "sensor-42", "s3cret", "iot")
