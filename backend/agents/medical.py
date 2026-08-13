"""AG-4 Medical Coordination — hospital allocation + ambulance dispatch."""
from __future__ import annotations
from app.models import Event, Recommendation, Geo
from app.resources import HOSPITALS, AMBULANCES
from app.geo_utils import distance_km
from .base import Agent


class MedicalCoordinationAgent(Agent):
    id = "AG-4"
    # dispatch decisions need confirmed ground-truth signal, not a forecast/imagery alone.
    triggers = frozenset({"iot"})

    def run(self, incident_id: str, events: list[Event], state: dict) -> Recommendation:
        ag1 = state.get("AG-1", {})
        ag2 = state.get("AG-2", {})
        severity = ag1.get("severity", 0.0)
        coords = (ag1.get("geo") or {}).get("coordinates") or [80.27, 13.08]
        lon, lat = coords[0], coords[1]
        affected = ag2.get("details", {}).get("affected_population", 0) or 0
        casualty_estimate = round(affected * 0.02)  # heuristic: 2% of affected need medical care

        candidates = [h for h in HOSPITALS if h["free_beds"] > 0]
        avail_amb = [a for a in AMBULANCES if a["status"] == "available"]

        if not candidates:
            action = "escalate:no_hospital_capacity"
            rationale = f"Est. {casualty_estimate} casualties; no hospital has free beds. Escalate to neighboring region."
            confidence, details = 0.4, {}
        else:
            best = min(candidates, key=lambda h: (
                -h["free_beds"] if h["free_beds"] >= casualty_estimate else 0,
                distance_km(lon, lat, h["lon"], h["lat"]),
            ))
            amb = min(avail_amb, key=lambda a: distance_km(lon, lat, a["lon"], a["lat"])) if avail_amb else None
            action = f"allocate:{best['id']}"
            rationale = (
                f"Est. {casualty_estimate} casualties. Allocate to {best['name']} "
                f"({best['free_beds']} free beds)."
                + (f" Dispatch ambulance {amb['id']}." if amb else " No ambulance available.")
            )
            confidence = 0.75
            details = {"hospital": best, "ambulance": amb, "casualty_estimate": casualty_estimate}

        rec = Recommendation(
            agent_id=self.id, incident_id=incident_id, action=action, severity=severity,
            evidence=(ag1.get("evidence", []) + ag2.get("evidence", [])) or ["no-evidence"],
            rationale=rationale, confidence=confidence,
            geo=Geo(type="Point", coordinates=[lon, lat]), details=details,
        )
        rec.validate_explainable()
        return rec
