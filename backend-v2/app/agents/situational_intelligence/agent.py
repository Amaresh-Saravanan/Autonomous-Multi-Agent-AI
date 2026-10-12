"""AG-8 Situational Intelligence (Phase 15). Reads the full blackboard
(every other agent's current output) and produces one rolling summary.
Runs last in the chain (Phase 16 orchestration order), so it's the only
agent allowed to cite every other agent as evidence."""

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.models.agent import AgentStatusEnum


class SituationalIntelligenceAgent(BaseAgent):
    id = "AG-8"
    triggers = frozenset({"iot", "weather", "satellite"})

    def execute(self, context: AgentContext) -> AgentResult:
        summary_parts: list[str] = []
        max_severity = 0.0

        for agent_id, agent_data in context.blackboard.items():
            if agent_id == self.id or not isinstance(agent_data, dict):
                continue
            severity = agent_data.get("severity", 0.0)
            max_severity = max(max_severity, severity)
            action = agent_data.get("action", "unknown")
            summary_parts.append(f"{agent_id}: {action} (severity {severity:.1f})")

        if not summary_parts:
            summary_parts = ["No other agents have reported yet."]

        reasoning_mode = "deterministic_fallback"
        reasoning = "Incident status: " + "; ".join(summary_parts) + ". Monitor and escalate if severity rises."
        confidence = 0.7

        if context.llm is not None:
            prompt = (
                f"Incident {context.incident_id} status:\n"
                + "\n".join(summary_parts)
                + "\n\nProvide ONE concise operational summary for the emergency command center "
                "(< 100 words). Focus on the most urgent item and the next recommended action."
            )
            llm_result = context.llm.reason(prompt, max_tokens=120)
            if llm_result.status == "SUCCESS":
                reasoning, reasoning_mode, confidence = llm_result.content, "llm", 0.9

        evidence = [k for k in context.blackboard if k != self.id] or ["no-prior-agent-reports"]

        return AgentResult(
            agent_id=self.id,
            incident_id=context.incident_id,
            status=AgentStatusEnum.SUCCESS,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence,
            recommendations=[{"action": "summarize", "severity": max_severity}],
            metadata={"reasoning_mode": reasoning_mode},
        )
