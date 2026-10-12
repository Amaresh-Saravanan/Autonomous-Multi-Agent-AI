"""Recommendation read + human-decision endpoints (Phase 17/18)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.errors import AuthorizationError
from app.infrastructure.database import get_db
from app.models.audit import ActorTypeEnum
from app.models.incident import Incident
from app.models.security import RoleEnum, User
from app.recommendations import service
from app.recommendations.schemas import RecommendationDecision, RecommendationResponse
from app.security.permissions import ROLE_RANK, require_role
from app.services.audit_service import record as audit_record

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationResponse])
def list_recommendations(
    incident_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.VIEWER)),
) -> list[RecommendationResponse]:
    return service.list_responses(db, user, incident_id=incident_id)


@router.post("/{recommendation_id}/decide", response_model=RecommendationResponse)
def decide_recommendation(
    recommendation_id: uuid.UUID,
    body: RecommendationDecision,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(RoleEnum.OPERATOR)),
) -> RecommendationResponse:
    if body.decision == "override" and ROLE_RANK[user.role] < ROLE_RANK[RoleEnum.ADMIN]:
        raise AuthorizationError("Only ADMIN may override a recommendation")
    rec = service.decide(
        db, recommendation_id, user,
        decision=body.decision, reason=body.reason, replacement_action=body.replacement_action,
    )
    # PRD SEC-2: every human decision is in the audit log.
    audit_record(
        db,
        actor_type=ActorTypeEnum.USER,
        actor_id=user.email,
        agency_id=user.agency_id,
        action=f"recommendation_{body.decision}",
        incident_id=rec.incident_id,
        recommendation_id=rec.id,
        metadata={"agent_id": rec.agent_id, "action": rec.action, "reason": body.reason, "status": rec.status.value},
    )
    return service.to_response(rec, db.get(Incident, rec.incident_id))
