"""AG-2 Damage Assessment — estimates affected population & structures from
AG-1's severity. Real imagery change-detection is Phase 3+; this is a
population-density heuristic, the honest ceiling for now.
"""
from __future__ import annotations
import math
from app.models import Event, Recommendation, Geo
from .base import Agent

POP_DENSITY_PER_KM2 = 4500
AFFECTED_RADIUS_KM = 2.0


class DamageAssessmentAgent(Agent):
    id = "AG-2"

    def run(self, incident_id: str, events: list[Event], state: dict) -> Recommendation:
        ag1 = state.get("AG-1", {})
        severity = ag1.get("severity", 0.0)
        geo = ag1.get("geo") or {"type": "Point", "coordinates": []}

        area_km2 = math.pi * AFFECTED_RADIUS_KM ** 2
        affected_population = round(severity * POP_DENSITY_PER_KM2 * area_km2 * 0.3)
        structures_damaged = round(severity * 40)

        rationale = (
            f"AG-1 severity {severity:.2f} within {AFFECTED_RADIUS_KM}km radius -> "
            f"est. {affected_population} people, {structures_damaged} structures affected "
            f"(population-density heuristic, not imagery change-detection)."
        )

        rec = Recommendation(
            agent_id=self.id, incident_id=incident_id, action="estimate_damage",
            severity=severity,
            evidence=ag1.get("evidence") or [e.event_id for e in events] or ["no-evidence"],
            rationale=rationale, confidence=0.55,
            geo=Geo(**geo) if geo.get("coordinates") else Geo(),
            details={"affected_population": affected_population, "structures_damaged": structures_damaged},
        )
        rec.validate_explainable()
        return rec
