"""Typed recommendation contracts (Phase 5/17/18)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    incident_id: uuid.UUID
    agent_id: str
    action: str
    priority: str
    confidence: float
    reasoning: str
    target_agency_id: uuid.UUID | None
    status: str
    created_at: datetime
    expires_at: datetime | None


class RecommendationDecision(BaseModel):
    """Body for approve/reject/override. `replacement_action` and `reason`
    are required for OVERRIDE, ignored otherwise."""

    decision: str  # "approve" | "reject" | "override"
    reason: str | None = None
    replacement_action: str | None = None


class HumanDecision(BaseModel):
    recommendation_id: uuid.UUID
    decision: str
    operator_id: uuid.UUID
    reason: str | None = None
