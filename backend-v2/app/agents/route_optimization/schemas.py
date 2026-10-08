"""AG-6 output shape (Phase 15)."""

from pydantic import BaseModel


class RouteRecommendation(BaseModel):
    destination: dict
    distance_km: float
    blocked: bool
