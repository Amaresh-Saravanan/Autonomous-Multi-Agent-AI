"""Per-agent node body (Phase 16). Builds a fresh `AgentContext` from the
current blackboard snapshot (so each agent sees the previous agents' fresh
output), runs the agent, merges the result back into the (Redis) blackboard,
and persists the AgentRun/AgentHealth/Recommendation/Audit side effects
that V1's orchestrator did inline. One agent's exception never reaches
here — `BaseAgent.run()` already turned it into a FAILED result."""

import uuid
from typing import TypedDict

from sqlalchemy.orm import Session

from app.agents.base import AgentContext, BaseAgent
from app.infrastructure.llm import LLMService
from app.models.audit import ActorTypeEnum
from app.models.incident import LocationStateEnum
from app.orchestration.conditions import should_run
from app.orchestration.state import BlackboardService
from app.recommendations.service import create_from_agent_result
from app.services.agent_health_service import record_run
from app.services.alert_service import publish_if_worthy
from app.services.audit_service import record as audit_record


class GraphState(TypedDict):
    incident_id: uuid.UUID
    event_id: uuid.UUID | None
    source_type: str | None
    severity: float
    location_state: LocationStateEnum
    latitude: float | None
    longitude: float | None
    events: list[dict]
    evidence_event_ids: list[str]
    resources: dict
    results: dict


def run_agent_node(agent: BaseAgent, *, db: Session, blackboard: BlackboardService, llm: LLMService | None):
    def node(state: GraphState) -> GraphState:
        incident_key = str(state["incident_id"])
        blackboard_snapshot = blackboard.get_incident(incident_key)

        context = AgentContext(
            incident_id=incident_key,
            source_type=state["source_type"],
            severity=state["severity"],
            location_state=state["location_state"],
            latitude=state["latitude"],
            longitude=state["longitude"],
            events=state["events"],
            evidence_event_ids=state["evidence_event_ids"],
            blackboard=blackboard_snapshot,
            resources=state["resources"],
            llm=llm,
        )

        if not should_run(agent, context):
            return state

        result = agent.run(context)

        first_rec = result.recommendations[0] if result.recommendations else {}
        blackboard_entry = {
            "severity": first_rec.get("severity", context.severity),
            "action": first_rec.get("action"),
            "evidence": result.evidence,
            "rationale": result.reasoning,
            "confidence": result.confidence,
            "details": first_rec.get("details", {}),
        }
        blackboard.merge(incident_key, agent.id, blackboard_entry)

        record_run(db, state["incident_id"], state["event_id"], result)

        rec = create_from_agent_result(db, state["incident_id"], result)
        audit_record(
            db,
            actor_type=ActorTypeEnum.AGENT,
            actor_id=agent.id,
            action="recommendation_created",
            incident_id=state["incident_id"],
            recommendation_id=rec.id,
            metadata={"status": result.status.value, "fallback_used": result.fallback_used},
        )
        publish_if_worthy(
            db,
            incident_id=state["incident_id"],
            agent_id=agent.id,
            action=rec.action,
            severity=blackboard_entry["severity"] or 0.0,
            target_agency_id=rec.target_agency_id,
            redis_client=blackboard.redis_client,
        )

        state["results"][agent.id] = result
        return state

    return node
