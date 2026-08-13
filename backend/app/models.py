"""Shared data models. Common Event schema per TDD 3.1."""
from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Geo(BaseModel):
    type: str = "Point"                     # Point | Polygon
    coordinates: list = Field(default_factory=list)  # GeoJSON [lon, lat]


class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    source_type: str                        # satellite|drone|iot|weather|social|gis|citizen
    source_id: str
    timestamp: str = Field(default_factory=_now)
    geo: Geo
    payload: dict = Field(default_factory=dict)
    confidence: float = 1.0
    ingested_at: str = Field(default_factory=_now)


class Recommendation(BaseModel):
    """Every agent output. evidence + rationale are REQUIRED (PRD AC-3, DS-7)."""
    rec_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_id: str
    incident_id: str
    action: str
    severity: float                         # 0..1
    evidence: list[str]                     # source event_ids — must be non-empty
    rationale: str
    confidence: float
    geo: Geo
    status: str = "pending"                 # pending|approved|rejected
    created_at: str = Field(default_factory=_now)
    details: dict = Field(default_factory=dict)  # structured hand-off to downstream agents
    target_agency: str | None = None        # None = visible to all agencies (tracker 3.5)

    def validate_explainable(self) -> None:
        # ponytail: this is the one guard that makes "explainable" real, not a promise
        assert self.evidence, "recommendation has no evidence (violates AC-3/DS-7)"
        assert self.rationale.strip(), "recommendation has no rationale"
