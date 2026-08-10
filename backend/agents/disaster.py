"""AG-1 Disaster Assessment — Phase 1 uses Groq (Mixtral-8x7B) for reasoning,
falls back to thresholds if LLM unavailable. All recommendations carry evidence.
"""
from __future__ import annotations
import json
from app.models import Event, Recommendation, Geo
from app import llm
from .base import Agent

# metric -> (warning_threshold, critical_threshold) for fallback
THRESHOLDS: dict[str, tuple[float, float]] = {
    "water_level": (3.0, 5.0),
}


class DisasterAssessmentAgent(Agent):
    id = "AG-1"

    def run(self, incident_id: str, events: list[Event], state: dict) -> Recommendation:
        if not events:
            return Recommendation(
                agent_id=self.id, incident_id=incident_id, action="monitor",
                severity=0.0, evidence=["no-events"], rationale="No events.",
                confidence=0.5, geo=Geo(),
            )

        # Try LLM first; fall back to thresholds if unavailable.
        if llm.available():
            return self._llm_reasoning(incident_id, events)
        else:
            return self._threshold_reasoning(incident_id, events)

    def _llm_reasoning(self, incident_id: str, events: list[Event]) -> Recommendation:
        # Format events for Groq to reason about
        events_summary = "\n".join([
            f"- {e.source_type} from {e.source_id}: {json.dumps(e.payload)}"
            for e in events
        ])
        prompt = f"""Analyze these disaster-related sensor/weather events and assess severity (0.0=low, 1.0=critical).
Return JSON: {{"severity": <float>, "action": "<str>", "rationale": "<str>"}}

Events:
{events_summary}

Be concise."""
        try:
            response = llm.reason(prompt, max_tokens=200)
            result = json.loads(response)
            severity = float(result.get("severity", 0.5))
            action = str(result.get("action", "monitor"))
            rationale = str(result.get("rationale", "LLM assessment."))
        except (json.JSONDecodeError, ValueError, KeyError):
            # Fallback if LLM response is malformed
            severity = 0.5
            action = "monitor"
            rationale = f"LLM response parsing failed; {response[:100]}"

        return Recommendation(
            agent_id=self.id, incident_id=incident_id, action=action,
            severity=min(max(severity, 0.0), 1.0),  # clamp to [0, 1]
            evidence=[e.event_id for e in events],
            rationale=rationale, confidence=0.85 if llm.available() else 0.6,
            geo=events[0].geo if events else Geo(),
        )

    def _threshold_reasoning(self, incident_id: str, events: list[Event]) -> Recommendation:
        worst_event: Event | None = None
        worst_severity = 0.0

        for e in events:
            metric = e.payload.get("metric")
            reading = e.payload.get("reading")
            bounds = THRESHOLDS.get(metric)
            if bounds is None or reading is None:
                continue
            warn, crit = bounds
            if reading < warn:
                severity = 0.0
            elif reading < crit:
                severity = 0.5 + 0.5 * (reading - warn) / (crit - warn)
            else:
                severity = 1.0
            if severity > worst_severity:
                worst_severity = severity
                worst_event = e

        if worst_event is None:
            action = "monitor"
            rationale = "No sensor readings crossed a configured threshold."
            evidence = [e.event_id for e in events]
            geo = Geo()
        else:
            action = "raise_severity" if worst_severity >= 0.5 else "monitor"
            rationale = (
                f"{worst_event.payload.get('metric')} reading "
                f"{worst_event.payload.get('reading')}{worst_event.payload.get('unit', '')} "
                f"from sensor {worst_event.source_id} exceeds warning threshold."
            )
            evidence = [worst_event.event_id]
            geo = worst_event.geo

        return Recommendation(
            agent_id=self.id, incident_id=incident_id, action=action,
            severity=worst_severity, evidence=evidence, rationale=rationale,
            confidence=1.0 if worst_event else 0.5, geo=geo,
        )
