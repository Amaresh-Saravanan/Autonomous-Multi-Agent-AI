"""AG-1 Disaster Assessment (Phase 15). LLM reasoning with a threshold
fallback — but unlike V1, an LLM failure or malformed response is never
reported as a successful rationale: it falls through to the threshold
path with `fallback_used=True` and the reason recorded in `metadata`."""

import json

from pydantic import ValidationError

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.disaster_assessment.prompts import build_prompt
from app.agents.disaster_assessment.rules import threshold_severity
from app.agents.disaster_assessment.schemas import AG1LLMOutput
from app.models.agent import AgentStatusEnum


class DisasterAssessmentAgent(BaseAgent):
    id = "AG-1"
    triggers = frozenset({"iot", "weather", "satellite"})

    def execute(self, context: AgentContext) -> AgentResult:
        if not context.events:
            return AgentResult(
                agent_id=self.id,
                incident_id=context.incident_id,
                status=AgentStatusEnum.SUCCESS,
                confidence=0.5,
                reasoning="No events to assess.",
                evidence=["no-events"],
                recommendations=[{"action": "monitor"}],
            )

        fallback_reason: str | None = None
        if context.llm is not None:
            llm_result, fallback_reason = self._try_llm(context)
            if llm_result is not None:
                return llm_result

        return self._threshold_reasoning(context, fallback_reason=fallback_reason)

    def _try_llm(self, context: AgentContext) -> tuple[AgentResult | None, str | None]:
        """Returns (result, None) on genuine LLM success, else (None, reason)
        so the threshold fallback can report exactly why it was used."""
        events_summary = "\n".join(
            f"- {e.get('source_type')} from {e.get('source_id', 'unknown')}: {json.dumps(e.get('payload', {}))}"
            for e in context.events
        )
        llm_result = context.llm.reason(build_prompt(events_summary), max_tokens=200)

        if llm_result.status != "SUCCESS":
            return None, llm_result.fallback_reason

        try:
            parsed = AG1LLMOutput.model_validate_json(llm_result.content)
        except (ValidationError, ValueError) as exc:
            return None, f"LLM response could not be parsed as structured JSON: {exc}"

        result = AgentResult(
            agent_id=self.id,
            incident_id=context.incident_id,
            status=AgentStatusEnum.SUCCESS,
            confidence=0.85,
            reasoning=parsed.rationale,
            evidence=context.evidence_event_ids or ["no-evidence"],
            recommendations=[{"action": parsed.action, "severity": parsed.severity}],
            metadata={"reasoning_mode": "llm", "model": llm_result.model},
        )
        return result, None

    def _threshold_reasoning(self, context: AgentContext, fallback_reason: str | None) -> AgentResult:
        worst_event: dict | None = None
        worst_severity = 0.0

        for e in context.events:
            payload = e.get("payload", {})
            metric, reading = payload.get("metric"), payload.get("reading")
            if metric is None or reading is None:
                continue
            severity = threshold_severity(metric, reading)
            if severity is not None and severity > worst_severity:
                worst_severity = severity
                worst_event = e

        if worst_event is None:
            action = "monitor"
            reasoning = "No sensor readings crossed a configured threshold."
            evidence = [e["event_id"] for e in context.events if "event_id" in e] or ["no-evidence"]
            confidence = 0.5
        else:
            payload = worst_event["payload"]
            action = "raise_severity" if worst_severity >= 0.5 else "monitor"
            reasoning = (
                f"{payload.get('metric')} reading {payload.get('reading')}{payload.get('unit', '')} "
                f"exceeds warning threshold."
            )
            evidence = [worst_event["event_id"]]
            confidence = 1.0

        status = AgentStatusEnum.DEGRADED if fallback_reason else AgentStatusEnum.SUCCESS
        metadata = {"reasoning_mode": "deterministic_fallback"}
        if fallback_reason:
            metadata["fallback_reason"] = fallback_reason

        return AgentResult(
            agent_id=self.id,
            incident_id=context.incident_id,
            status=status,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence,
            recommendations=[{"action": action, "severity": worst_severity}],
            fallback_used=bool(fallback_reason),
            metadata=metadata,
        )
