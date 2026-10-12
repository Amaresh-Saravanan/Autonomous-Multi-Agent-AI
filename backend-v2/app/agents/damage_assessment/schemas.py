"""AG-2 output shape (Phase 15)."""

from pydantic import BaseModel


class DamageEstimate(BaseModel):
    affected_population: int
    structures_damaged: int
    method: str = "population_density_heuristic"
