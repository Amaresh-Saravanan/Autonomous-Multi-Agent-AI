"""AG-5 output shape + allocation strategy interface (Phase 15)."""

from typing import Protocol

from pydantic import BaseModel


class AllocationPlan(BaseModel):
    shelter: dict | None = None
    needed: dict[str, float]
    shortfalls: dict[str, float]


class AllocationStrategy(Protocol):
    def allocate(self, *, lat: float, lon: float, affected: int, shelters: list[dict], supplies: dict) -> AllocationPlan: ...
