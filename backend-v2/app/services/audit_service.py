"""Persistent, append-only audit (Phase 20). Replaces V1's in-memory list.
No update/delete method exists on this service — that is the enforcement
of "append-only" at the application level."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import ActorTypeEnum, AuditLog


def record(
    db: Session,
    *,
    actor_type: ActorTypeEnum,
    actor_id: str,
    action: str,
    agency_id: uuid.UUID | None = None,
    incident_id: uuid.UUID | None = None,
    recommendation_id: uuid.UUID | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        timestamp=datetime.now(timezone.utc),
        actor_type=actor_type,
        actor_id=actor_id,
        agency_id=agency_id,
        action=action,
        incident_id=incident_id,
        recommendation_id=recommendation_id,
        metadata_json=metadata or {},
    )
    db.add(entry)
    db.commit()
    return entry


def list_for_incident(db: Session, incident_id: uuid.UUID) -> list[AuditLog]:
    return list(
        db.scalars(select(AuditLog).where(AuditLog.incident_id == incident_id).order_by(AuditLog.timestamp))
    )
