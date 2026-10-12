"""Dev/demo bootstrap (Phase A): creates the one agency, admin user, demo
resources, and IoT device a fresh V2 deploy needs to be loggable-into and
demo-able. Idempotent — safe to run more than once against the same DB.

Usage: python -m scripts.seed  (from backend-v2/)
"""

import os
import secrets

from app.infrastructure.database import session_scope
from app.models.resource import Hospital, RescueTeam, Resource, Shelter
from app.models.security import Agency, Device, DeviceStatusEnum, RoleEnum, User
from app.security.auth import hash_password

AGENCY_CODE = "DEFAULT"
AGENCY_NAME = "Default Agency"


def _get_or_create_agency(db) -> Agency:
    agency = db.query(Agency).filter(Agency.code == AGENCY_CODE).first()
    if agency is None:
        agency = Agency(name=AGENCY_NAME, code=AGENCY_CODE)
        db.add(agency)
        db.flush()
    return agency


def _get_or_create_admin(db, agency: Agency) -> tuple[User, str | None]:
    email = os.environ.get("SEED_ADMIN_EMAIL", "admin@example.com")
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        return existing, None
    password = os.environ.get("SEED_ADMIN_PASSWORD") or secrets.token_urlsafe(12)
    user = User(
        email=email,
        hashed_password=hash_password(password),
        role=RoleEnum.ADMIN,
        agency_id=agency.id,
    )
    db.add(user)
    db.flush()
    return user, password


def _seed_resources(db, agency: Agency) -> None:
    if db.query(Shelter).filter(Shelter.agency_id == agency.id).first() is not None:
        return  # already seeded for this agency
    db.add_all(
        [
            Shelter(name="Community Hall", agency_id=agency.id, latitude=13.07, longitude=80.26, capacity=300, occupied=100),
            Hospital(name="Coastal General", agency_id=agency.id, latitude=13.05, longitude=80.28, beds_total=50, beds_free=10, ambulances_total=3, ambulances_free=2),
            RescueTeam(name="Alpha", agency_id=agency.id, latitude=13.06, longitude=80.27),
            Resource(name="Food", category="food_units", agency_id=agency.id, quantity=5000),
            Resource(name="Water", category="water_liters", agency_id=agency.id, quantity=20000),
            Resource(name="Blankets", category="blankets", agency_id=agency.id, quantity=1500),
        ]
    )


def _get_or_create_device(db, agency: Agency) -> tuple[Device, str | None]:
    device_id = os.environ.get("SEED_DEVICE_ID", "demo-sensor-01")
    existing = db.query(Device).filter(Device.device_id == device_id).first()
    if existing is not None:
        return existing, None
    secret = os.environ.get("SEED_DEVICE_SECRET") or secrets.token_urlsafe(12)
    device = Device(
        device_id=device_id,
        hashed_secret=hash_password(secret),
        agency_id=agency.id,
        source_type="iot",
        status=DeviceStatusEnum.ACTIVE,
    )
    db.add(device)
    db.flush()
    return device, secret


def main() -> None:
    with session_scope() as db:
        agency = _get_or_create_agency(db)
        user, admin_password = _get_or_create_admin(db, agency)
        _seed_resources(db, agency)
        device, device_secret = _get_or_create_device(db, agency)

    print("Seed complete.")
    print(f"  Agency: {agency.name} ({agency.code})")
    print(f"  Admin login: {user.email} / {admin_password if admin_password else '(already existed, password unchanged)'}")
    print(f"  Demo device: id={device.device_id} secret={device_secret if device_secret else '(already existed, secret unchanged)'}")


if __name__ == "__main__":
    main()
