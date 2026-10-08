"""Device authentication for ingestion (Phase 7). Ingestion is never
publicly writable: every ingest call must carry valid device credentials,
and a device may only submit the `source_type` it was provisioned for."""

from datetime import datetime, timezone

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.errors import AuthenticationError, AuthorizationError
from app.infrastructure.database import get_db
from app.models.security import Device, DeviceStatusEnum
from app.security.auth import verify_password


def authenticate_device(db: Session, device_id: str, secret: str, source_type: str) -> Device:
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device or device.status != DeviceStatusEnum.ACTIVE:
        raise AuthenticationError("Invalid or revoked device credentials")
    if not verify_password(secret, device.hashed_secret):
        raise AuthenticationError("Invalid or revoked device credentials")
    if device.source_type != source_type:
        raise AuthorizationError(
            f"Device '{device_id}' is not authorized to submit source_type='{source_type}'"
        )
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    return device


def require_device(source_type: str):
    def dependency(
        x_device_id: str = Header(...),
        x_device_secret: str = Header(...),
        db: Session = Depends(get_db),
    ) -> Device:
        return authenticate_device(db, x_device_id, x_device_secret, source_type)

    return dependency
