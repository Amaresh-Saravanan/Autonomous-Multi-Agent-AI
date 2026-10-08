"""Resource snapshot endpoint — matches V1's `/resources` for the frontend
dashboard (Phase 25 compat)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.models.security import RoleEnum, User
from app.security.permissions import require_role
from app.services.resource_service import load_resource_snapshot

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])


@router.get("")
def get_resources(db: Session = Depends(get_db), user: User = Depends(require_role(RoleEnum.VIEWER))) -> dict:
    return load_resource_snapshot(db)
