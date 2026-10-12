"""Persistent RecommendationService (Phase 17/18). Replaces V1's in-memory
list. Agency filtering is enforced here in the query, not left to the
frontend — and unlike V1, a NULL `target_agency_id` is never treated as
"visible to everyone": `list_for_user` only returns rows whose agency
matches the caller (or any row, for ADMIN)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import AgentResult
from app.errors import NotFoundError, ValidationError
from app.models.recommendation import Recommendation, RecommendationStatusEnum
from app.models.security import RoleEnum, User
from app.security.permissions import require_agency_access

# Which `details` key on an agent's recommendation names the resource whose
# owning agency the recommendation should be scoped to.
_RESOURCE_KEY_BY_AGENT = {
    "AG-3": "assigned_team",
    "AG-4": "hospital",
    "AG-5": "shelter",
    "AG-6": "destination",
}


def _derive_priority(result: AgentResult) -> str:
    details = result.recommendations[0].get("details", {}) if result.recommendations else {}
    if "priority" in details:
        return details["priority"]
    if result.confidence >= 0.85:
        return "critical"
    if result.confidence >= 0.5:
        return "high"
    return "routine"


def _derive_target_agency_id(result: AgentResult) -> uuid.UUID | None:
    if not result.recommendations:
        return None
    details = result.recommendations[0].get("details", {})
    resource_key = _RESOURCE_KEY_BY_AGENT.get(result.agent_id)
    if resource_key is None:
        return None
    resource = details.get(resource_key)
    if not resource or "agency_id" not in resource:
        return None
    return uuid.UUID(resource["agency_id"])


def create_from_agent_result(db: Session, incident_id: uuid.UUID, result: AgentResult) -> Recommendation:
    action = result.recommendations[0]["action"] if result.recommendations else "none"
    rec = Recommendation(
        incident_id=incident_id,
        agent_id=result.agent_id,
        action=action,
        priority=_derive_priority(result),
        confidence=result.confidence,
        reasoning=result.reasoning,
        target_agency_id=_derive_target_agency_id(result),
        status=RecommendationStatusEnum.PENDING,
    )
    db.add(rec)
    db.commit()
    return rec


def get(db: Session, recommendation_id: uuid.UUID) -> Recommendation:
    rec = db.get(Recommendation, recommendation_id)
    if rec is None:
        raise NotFoundError(f"Recommendation {recommendation_id} not found")
    return rec


def list_for_user(db: Session, user: User, *, incident_id: uuid.UUID | None = None) -> list[Recommendation]:
    stmt = select(Recommendation)
    if incident_id is not None:
        stmt = stmt.where(Recommendation.incident_id == incident_id)
    if user.role != RoleEnum.ADMIN:
        stmt = stmt.where(Recommendation.target_agency_id == user.agency_id)
    return list(db.scalars(stmt.order_by(Recommendation.created_at.desc())))


def decide(
    db: Session,
    recommendation_id: uuid.UUID,
    user: User,
    *,
    decision: str,
    reason: str | None = None,
    replacement_action: str | None = None,
) -> Recommendation:
    """approve | reject | override. Only a still-PENDING recommendation can
    be decided — this is V2's equivalent of V1's "stale decision must not
    resurrect an older state" guard, translated to a persisted row: a
    second decision on an already-decided recommendation is rejected
    outright rather than silently overwriting the first."""
    rec = get(db, recommendation_id)
    require_agency_access(user, rec.target_agency_id)

    if rec.status != RecommendationStatusEnum.PENDING:
        raise ValidationError(f"Recommendation {recommendation_id} is already {rec.status.value}; cannot decide again")

    if decision == "approve":
        rec.status = RecommendationStatusEnum.APPROVED
    elif decision == "reject":
        rec.status = RecommendationStatusEnum.REJECTED
    elif decision == "override":
        if not replacement_action or not reason:
            raise ValidationError("override requires both replacement_action and reason")
        rec.status = RecommendationStatusEnum.OVERRIDDEN
        rec.override_action = replacement_action
    else:
        raise ValidationError(f"Unknown decision '{decision}'")

    rec.decided_by_user_id = user.id
    rec.decided_at = datetime.now(timezone.utc)
    rec.decision_reason = reason
    db.commit()
    return rec
