"""Persistent RecommendationService (Phase 17/18). Replaces V1's in-memory
list. Agency filtering is enforced here in the query, not left to the
frontend — and unlike V1, a NULL `target_agency_id` is never treated as
"visible to everyone": `list_for_user` only returns rows whose agency
matches the caller (or any row, for ADMIN)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.agents.base import AgentResult
from app.errors import NotFoundError, ValidationError
from app.models.incident import Incident, LocationStateEnum
from app.models.recommendation import Recommendation, RecommendationStatusEnum
from app.models.security import RoleEnum, User
from app.recommendations.schemas import RecommendationResponse
from app.security.permissions import require_agency_access

# Which `details` key on an agent's recommendation names the resource whose
# owning agency the recommendation should be scoped to.
_RESOURCE_KEY_BY_AGENT = {
    "AG-3": "assigned_team",
    "AG-4": "hospital",
    "AG-5": "shelter",
    "AG-6": "destination",
}


# Situation-level agents (disaster/damage assessment and the situational
# summary) describe the incident itself, not one agency's resources, so they
# are explicitly flagged global. This is an opt-in flag, NOT a NULL-agency
# fallback: an agent whose agency can't be resolved stays admin-only.
GLOBAL_AGENTS = frozenset({"AG-1", "AG-2", "AG-8"})


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


def create_from_agent_result(
    db: Session, incident_id: uuid.UUID, result: AgentResult, *, severity: float | None = None
) -> Recommendation:
    first = result.recommendations[0] if result.recommendations else {}
    action = first.get("action", "none")
    rec = Recommendation(
        incident_id=incident_id,
        agent_id=result.agent_id,
        action=action,
        priority=_derive_priority(result),
        confidence=result.confidence,
        reasoning=result.reasoning,
        severity=float(severity if severity is not None else (first.get("severity") or 0.0)),
        evidence_json=list(result.evidence),
        details_json=first.get("details", {}),
        target_agency_id=_derive_target_agency_id(result),
        is_global=result.agent_id in GLOBAL_AGENTS,
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
        stmt = stmt.where(
            or_(Recommendation.target_agency_id == user.agency_id, Recommendation.is_global.is_(True))
        )
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
    if not rec.is_global:  # global recs are decidable by any operator (route enforces role)
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


def to_response(rec: Recommendation, incident: Incident | None) -> RecommendationResponse:
    """Enrich a stored recommendation with what the console map needs: a
    Point geometry from the incident (only when the location is actually
    known — never fabricated) and, for AG-6, a straight-line `route_line`
    to the chosen destination (the routing provider is a straight-line
    fallback today, so this is exactly what the route is)."""
    resp = RecommendationResponse.model_validate(rec)
    resp.severity = rec.severity or 0.0
    resp.evidence = list(rec.evidence_json or [])
    details = dict(rec.details_json or {})

    located = (
        incident is not None
        and incident.latitude is not None
        and incident.longitude is not None
        and incident.location_state != LocationStateEnum.UNKNOWN
    )
    if located:
        resp.geo = {"type": "Point", "coordinates": [incident.longitude, incident.latitude]}
        dest = details.get("destination") or {}
        if rec.agent_id == "AG-6" and "lat" in dest and "lon" in dest:
            details["route_line"] = [[incident.longitude, incident.latitude], [dest["lon"], dest["lat"]]]
    resp.details = details
    return resp


def list_responses(
    db: Session, user: User, *, incident_id: uuid.UUID | None = None
) -> list[RecommendationResponse]:
    recs = list_for_user(db, user, incident_id=incident_id)
    ids = {r.incident_id for r in recs}
    incidents = {i.id: i for i in db.scalars(select(Incident).where(Incident.id.in_(ids)))} if ids else {}
    return [to_response(r, incidents.get(r.incident_id)) for r in recs]
