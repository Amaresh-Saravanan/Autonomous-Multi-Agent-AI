"""First-run bootstrap: `python -m app.seed`.

Creates what a fresh deployment needs before anyone can log in or any
sensor can report — agencies, an ADMIN user, and ingestion devices — and
nothing else unless asked. Idempotent: re-running never duplicates rows and
never rotates an existing secret.

Environment:
  SEED_ADMIN_EMAIL      default admin@example.com
  SEED_ADMIN_PASSWORD   if unset, a random one is generated and printed ONCE
  SEED_DEMO=1           also create an operator + viewer, demo resources
  SEED_DEVICES          comma list of source types to provision a device for
                        (default "citizen,iot")
  <TYPE>_DEVICE_SECRET  optional fixed secret for that device (e.g.
                        CITIZEN_DEVICE_SECRET); otherwise generated + printed

Generated secrets are shown once and stored only as argon2 hashes.
"""

import os
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database import session_scope
from app.models.resource import Hospital
from app.models.security import Agency, Device, RoleEnum, User
from app.security.auth import hash_password
from app.services.resource_service import seed_dev_resources

AGENCIES = [
    ("City Emergency Management", "city_emergency_mgmt"),
    ("Regional Health Department", "regional_health_dept"),
]


def _agency(db: Session, name: str, code: str) -> Agency:
    agency = db.scalar(select(Agency).where(Agency.code == code))
    if agency is None:
        agency = Agency(name=name, code=code)
        db.add(agency)
        db.flush()
    return agency


def _user(db: Session, email: str, password: str, role: RoleEnum, agency: Agency) -> bool:
    if db.scalar(select(User).where(User.email == email)):
        return False
    db.add(User(email=email, hashed_password=hash_password(password), role=role, agency_id=agency.id))
    return True


def _device(db: Session, source_type: str, agency: Agency) -> tuple[str, str | None]:
    device_id = f"{source_type}-default"
    if db.scalar(select(Device).where(Device.device_id == device_id)):
        return device_id, None
    secret = os.environ.get(f"{source_type.upper()}_DEVICE_SECRET") or secrets.token_urlsafe(32)
    db.add(Device(
        device_id=device_id, hashed_secret=hash_password(secret),
        agency_id=agency.id, source_type=source_type,
    ))
    return device_id, secret


def run() -> None:
    admin_email = os.environ.get("SEED_ADMIN_EMAIL", "admin@example.com")
    admin_password = os.environ.get("SEED_ADMIN_PASSWORD")
    generated_password = admin_password is None
    admin_password = admin_password or secrets.token_urlsafe(16)
    demo = os.environ.get("SEED_DEMO") == "1"
    device_types = [t.strip() for t in os.environ.get("SEED_DEVICES", "citizen,iot").split(",") if t.strip()]

    with session_scope() as db:
        agencies = [_agency(db, name, code) for name, code in AGENCIES]
        primary = agencies[0]

        print("== seed ==")
        if _user(db, admin_email, admin_password, RoleEnum.ADMIN, primary):
            print(f"admin user:   {admin_email}" + (f"  password: {admin_password}  (shown once)" if generated_password else ""))
        else:
            print(f"admin user:   {admin_email} already exists (unchanged)")

        if demo:
            for email, role, agency in [
                ("operator@example.com", RoleEnum.OPERATOR, primary),
                ("viewer@example.com", RoleEnum.VIEWER, agencies[1]),
            ]:
                pw = os.environ.get("SEED_DEMO_PASSWORD") or secrets.token_urlsafe(12)
                if _user(db, email, pw, role, agency):
                    print(f"demo user:    {email}  password: {pw}  (shown once)")
            if not db.scalar(select(Hospital).limit(1)):
                seed_dev_resources(db, primary.id)
                print("demo data:    resources seeded")

        for source_type in device_types:
            device_id, secret = _device(db, source_type, primary)
            if secret:
                print(f"device:       {device_id}  secret: {secret}  (shown once)")
            else:
                print(f"device:       {device_id} already exists (unchanged)")


if __name__ == "__main__":
    run()
