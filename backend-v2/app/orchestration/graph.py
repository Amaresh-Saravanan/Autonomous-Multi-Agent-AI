"""LangGraph wiring (Phase 16). The graph shape is still a chain (same
data dependency as V1), but unlike V1 each node is conditionally skipped
by `conditions.should_run` rather than unconditionally executed — see
`docs/archive/BACKEND_V2_MIGRATION.md` for why this isn't the "uncontrolled
autonomous loop" the spec warns against: it is a bounded, acyclic,
human-supervised chain that always terminates."""

import logging
import threading
import uuid

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.incidents.service import IncidentService
from app.infrastructure.database import session_scope
from app.infrastructure.llm import get_llm_service
from app.infrastructure.queue import get_queue_service
from app.models.agent import AgentStatusEnum
from app.models.audit import ActorTypeEnum
from app.models.incident import Event
from app.orchestration.execution import GraphState, run_agent_node
from app.orchestration.router import AGENT_CHAIN
from app.orchestration.state import BlackboardService, get_blackboard_service
from app.recommendations.conflict import ConflictDetector
from app.services.audit_service import record as audit_record
from app.services.resource_service import load_resource_snapshot

logger = logging.getLogger("app.orchestration")


def build_graph(db: Session, blackboard: BlackboardService):
    llm = get_llm_service()
    builder = StateGraph(GraphState)
    prev_id = None
    for agent in AGENT_CHAIN:
        builder.add_node(agent.id, run_agent_node(agent, db=db, blackboard=blackboard, llm=llm))
        if prev_id is None:
            builder.set_entry_point(agent.id)
        else:
            builder.add_edge(prev_id, agent.id)
        prev_id = agent.id
    builder.add_edge(prev_id, END)
    return builder.compile()


def run_for_event(db: Session, event_id: uuid.UUID, blackboard: BlackboardService | None = None) -> dict:
    """Entry point the queue worker calls (Phase 8/16). Runs the full agent
    chain for one event, then conflict detection, then updates the
    incident's rolling severity from AG-1's result."""
    blackboard = blackboard or get_blackboard_service()
    event = db.get(Event, event_id)
    if event is None:
        raise ValueError(f"Event {event_id} not found")

    incidents = IncidentService(db)
    incident = incidents.get(event.incident_id)

    initial_state: GraphState = {
        "incident_id": incident.id,
        "event_id": event.id,
        "source_type": event.source_type,
        "severity": incident.severity,
        "location_state": incident.location_state,
        "latitude": incident.latitude,
        "longitude": incident.longitude,
        "events": [{"event_id": str(event.id), "source_type": event.source_type, "payload": event.payload}],
        "evidence_event_ids": [str(event.id)],
        "resources": load_resource_snapshot(db),
        "results": {},
    }

    graph = build_graph(db, blackboard)
    final_state = graph.invoke(initial_state)

    blackboard_snapshot = blackboard.get_incident(str(incident.id))
    conflicts = ConflictDetector().detect(blackboard_snapshot)
    if conflicts:
        audit_record(
            db,
            actor_type=ActorTypeEnum.SYSTEM,
            actor_id="conflict_detector",
            action="conflict_detected",
            incident_id=incident.id,
            metadata={"conflicts": [c.__dict__ for c in conflicts]},
        )

    ag1_result = final_state["results"].get("AG-1")
    if ag1_result is not None and ag1_result.status != AgentStatusEnum.FAILED and ag1_result.recommendations:
        severity = ag1_result.recommendations[0].get("severity")
        if severity is not None:
            incidents.update_severity(incident.id, severity)

    return {"incident_id": str(incident.id), "conflicts": [c.__dict__ for c in conflicts], "results": final_state["results"]}


def _worker_loop(stop_event: threading.Event) -> None:
    """Drains the ingestion queue in a background thread (Phase 16) so the
    HTTP ingestion request never blocks on agent/LLM execution."""
    queue = get_queue_service()
    while not stop_event.is_set():
        job = queue.dequeue(timeout=1.0)
        if job is None:
            continue
        try:
            with session_scope() as db:
                run_for_event(db, uuid.UUID(job["event_id"]))
        except Exception:
            logger.exception("Failed processing queue job %s", job)


def start_worker_thread() -> threading.Event:
    stop_event = threading.Event()
    threading.Thread(target=_worker_loop, args=(stop_event,), daemon=True).start()
    return stop_event
