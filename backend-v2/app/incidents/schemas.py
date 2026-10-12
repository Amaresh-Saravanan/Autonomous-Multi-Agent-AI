"""Typed incident contracts (Phase 5). `IncidentCreate` is intentionally not
defined yet — nothing in V2 creates an incident directly via the API today
(incidents are only derived from ingested events); add it when a manual/
admin incident-creation endpoint actually exists, not before."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    severity: float
    location_state: str
    latitude: float | None
    longitude: float | None
    district: str | None
    state_region: str | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
