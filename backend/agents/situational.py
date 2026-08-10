"""AG-8 Situational Intelligence — reads full blackboard, summarizes state,
produces explainable rolling summary for the command center.
"""
from __future__ import annotations
from app.models import Recommendation, Geo
from app import llm
from .base import Agent


class SituationalIntelligenceAgent(Agent):
    id = "AG-8"

    def run(self, incident_id: str, events, state: dict) -> Recommendation:
        """Read the full blackboard (state) and produce a summary recommendation."""
        # Gather what other agents have discovered
        summary_parts = []
        max_severity = 0.0

        for agent_id, agent_data in state.items():
            if agent_id == self.id or not isinstance(agent_data, dict):
                continue
            severity = agent_data.get("severity", 0)
            max_severity = max(max_severity, severity)
            action = agent_data.get("action", "unknown")
            summary_parts.append(f"{agent_id}: {action} (severity {severity:.1f})")

        if not summary_parts:
            summary_parts = ["No other agents have reported yet."]

        # Optionally use LLM to synthesize; fall back to simple join if unavailable
        if llm.available():
            prompt = f"""Incident {incident_id} status:
{chr(10).join(summary_parts)}

Provide ONE concise operational summary for the emergency command center (< 100 words).
Focus on the most urgent item and the next recommended action."""
            rationale = llm.reason(prompt, max_tokens=120)
        else:
            rationale = "Incident status: " + "; ".join(summary_parts) + ". Monitor and escalate if severity rises."

        rec = Recommendation(
            agent_id=self.id,
            incident_id=incident_id,
            action="summarize",
            severity=max_severity,
            # ponytail: evidence must match what the loop above actually read
            # (excludes self), with a fallback for a fresh/empty blackboard —
            # otherwise AG-8 cites itself as evidence for its own summary.
            evidence=[k for k in state if k != self.id] or ["no-prior-agent-reports"],
            rationale=rationale,
            confidence=0.9 if llm.available() else 0.7,
            geo=Geo(),
        )
        rec.validate_explainable()
        return rec
