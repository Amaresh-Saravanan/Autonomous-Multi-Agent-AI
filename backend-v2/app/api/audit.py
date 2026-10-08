"""Audit read endpoint (Phase 20), ADMIN-only like V1."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models.audit import AuditLog
from app.models.security import RoleEnum, User
from app.security.permissions import require_role

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("")
def list_audit(db: Session = Depends(get_db), user: User = Depends(require_role(RoleEnum.ADMIN))) -> list[dict]:
    rows = db.scalars(select(AuditLog).order_by(AuditLog.timestamp.desc()))
    return [
        {
            "id": str(r.id), "timestamp": r.timestamp.isoformat(), "actor_type": r.actor_type.value,
            "actor_id": r.actor_id, "action": r.action,
            "incident_id": str(r.incident_id) if r.incident_id else None,
            "recommendation_id": str(r.recommendation_id) if r.recommendation_id else None,
            "metadata": r.metadata_json,
        }
        for r in rows
    ]
