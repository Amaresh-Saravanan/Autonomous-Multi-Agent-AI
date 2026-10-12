"""AG-3 output shape (Phase 15)."""

from pydantic import BaseModel


class RescueAssignment(BaseModel):
    assigned_team_id: str
    assigned_team_name: str
    distance_km: float
    priority: str
