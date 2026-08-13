"""AG-5 Resource Allocation — greedy shelter + supply allocation.
ponytail: greedy nearest-fit, not OR-Tools VRP. Upgrade when allocations
need to be jointly optimized across multiple simultaneous incidents.
"""
from __future__ import annotations
from app.models import Event, Recommendation, Geo
from app.resources import SHELTERS, SUPPLIES
from app.geo_utils import distance_km
from .base import Agent

SUPPLIES_PER_PERSON = {"food_units": 3, "water_liters": 10, "blankets": 1}


class ResourceAllocationAgent(Agent):
    id = "AG-5"
    # dispatch decisions need confirmed ground-truth signal, not a forecast/imagery alone.
    triggers = frozenset({"iot"})

    def run(self, incident_id: str, events: list[Event], state: dict) -> Recommendation:
        ag1 = state.get("AG-1", {})
        ag2 = state.get("AG-2", {})
        severity = ag1.get("severity", 0.0)
        coords = (ag1.get("geo") or {}).get("coordinates") or [80.27, 13.08]
        lon, lat = coords[0], coords[1]
        affected = ag2.get("details", {}).get("affected_population", 0) or 0

        open_shelters = [s for s in SHELTERS if s["capacity"] - s["occupied"] > 0]
        needed = {k: affected * v for k, v in SUPPLIES_PER_PERSON.items()}
        shortfalls = {k: max(0, needed[k] - SUPPLIES[k]) for k in needed}

        if not open_shelters:
            action = "escalate:no_shelter_capacity"
            rationale = f"Est. {affected} affected; no shelter has free capacity."
            confidence, details = 0.4, {"needed": needed, "shortfalls": shortfalls}
        else:
            best = min(open_shelters, key=lambda s: distance_km(lon, lat, s["lon"], s["lat"]))
            free = best["capacity"] - best["occupied"]
            action = f"allocate_shelter:{best['id']}"
            rationale = (
                f"Est. {affected} affected -> route to {best['name']} ({free} free capacity). "
                f"Supplies needed: {needed}."
            )
            if any(shortfalls.values()):
                rationale += f" SHORTFALL vs current stock: {shortfalls} — request resupply."
            confidence = 0.7
            details = {"shelter": best, "needed": needed, "shortfalls": shortfalls}

        rec = Recommendation(
            agent_id=self.id, incident_id=incident_id, action=action, severity=severity,
            evidence=(ag1.get("evidence", []) + ag2.get("evidence", [])) or ["no-evidence"],
            rationale=rationale, confidence=confidence,
            geo=Geo(type="Point", coordinates=[lon, lat]), details=details,
        )
        rec.validate_explainable()
        return rec
