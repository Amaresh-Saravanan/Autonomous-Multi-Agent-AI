"""Incident read endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.incidents.schemas import IncidentResponse
from app.incidents.service import IncidentService
from app.infrastructure.database import get_db
from app.models.security import RoleEnum
from app.security.permissions import require_role

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentResponse])
def list_incidents(db: Session = Depends(get_db), user=Depends(require_role(RoleEnum.VIEWER))) -> list[IncidentResponse]:
    return IncidentService(db).list_all()


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: uuid.UUID, db: Session = Depends(get_db), user=Depends(require_role(RoleEnum.VIEWER))
) -> IncidentResponse:
    return IncidentService(db).get(incident_id)
