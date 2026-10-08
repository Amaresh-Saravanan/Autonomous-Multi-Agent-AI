"""Alert read endpoint (Phase 21), agency-filtered."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models.security import RoleEnum, User
from app.security.permissions import require_role
from app.services.alert_service import list_for_user

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("")
def list_alerts(db: Session = Depends(get_db), user: User = Depends(require_role(RoleEnum.VIEWER))) -> list[dict]:
    return [
        {
            "id": str(a.id), "incident_id": str(a.incident_id), "level": a.level.value,
            "message": a.message, "status": a.status.value, "created_at": a.created_at.isoformat(),
        }
        for a in list_for_user(db, user)
    ]
