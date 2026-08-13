"""Agent orchestration via LangGraph (TDD 4.3, tracker 2.1).

Graph nodes = agents, chained in the existing data-dependency order
(AG-1 defines the incident; AG-8 summarizes last). Each node performs the
same side effects the old main.py loop did: refresh blackboard state, run
the agent, merge its output back into the blackboard, record the
recommendation, and (for AG-1) update the severity grid.

Trigger-based selective scheduling (only running agents relevant to an event
type) is implemented via AGENT_EVENT_TYPES and _should_run() — agents are
skipped when no event in the current batch matches their declared relevant
source_type(s).
"""
from __future__ import annotations
from typing import TypedDict

from langgraph.graph import StateGraph, END

from . import blackboard
from . import recommendations
from . import severity_grid
from .models import Event
from agents.disaster import DisasterAssessmentAgent
from agents.damage import DamageAssessmentAgent
from agents.rescue import RescuePlanningAgent
from agents.medical import MedicalCoordinationAgent
from agents.allocation import ResourceAllocationAgent
from agents.route import RouteOptimizationAgent
from agents.situational import SituationalIntelligenceAgent

AGENT_EVENT_TYPES: dict[str, frozenset[str] | None] = {
    # None = always runs, no event-type filter.
    "AG-1": None,   # defines the incident from any signal
    "AG-2": None,   # pure function of AG-1's output, not of event payload —
                    # keep in lockstep with AG-1 rather than filtering
    "AG-3": frozenset({"iot", "satellite", "weather"}),
    "AG-4": frozenset({"iot", "satellite", "weather"}),
    "AG-5": frozenset({"iot", "satellite", "weather"}),
    "AG-6": frozenset({"iot", "satellite", "weather"}),
    "AG-8": None,   # always summarizes the latest full blackboard
}
# ponytail: source_type is a proxy for "did AG-1/AG-2's output change," not the
# real dependency — AG-3..AG-6 only ever read blackboard state, never the event
# itself. If AG-1's LLM path starts deriving severity from event content in a
# way that doesn't correlate with source_type, this proxy can go stale. Upgrade:
# trigger on "did state[AG-1]/state[AG-2] actually change" if that's observed.


def _should_run(agent_id: str, events: list[Event]) -> bool:
    relevant = AGENT_EVENT_TYPES.get(agent_id)
    if relevant is None:
        return True
    return any(e.source_type in relevant for e in events)


AGENTS = [
    DisasterAssessmentAgent(),
    DamageAssessmentAgent(),
    RescuePlanningAgent(),
    MedicalCoordinationAgent(),
    ResourceAllocationAgent(),
    RouteOptimizationAgent(),
    SituationalIntelligenceAgent(),
]


class OrchestratorState(TypedDict):
    incident_id: str
    events: list[Event]
    recs: list[dict]


def _make_node(agent):
    def node(state: OrchestratorState) -> OrchestratorState:
        if not _should_run(agent.id, state["events"]):
            return state
        current = blackboard.get(state["incident_id"])  # refresh after prior agents
        rec = agent.run(state["incident_id"], state["events"], current)
        rec_dict = rec.model_dump()
        blackboard.merge(state["incident_id"], {agent.id: rec_dict})
        recommendations.record(rec_dict)
        # DS-1 severity heat-map (tracker 1.5): AG-1 defines disaster severity.
        if agent.id == "AG-1" and rec.geo.type == "Point" and len(rec.geo.coordinates) == 2:
            lon, lat = rec.geo.coordinates
            severity_grid.update(state["incident_id"], lat, lon, rec.severity)
        state["recs"].append(rec_dict)
        return state
    return node


def _build_graph():
    builder = StateGraph(OrchestratorState)
    prev_name = None
    for agent in AGENTS:
        builder.add_node(agent.id, _make_node(agent))
        if prev_name is None:
            builder.set_entry_point(agent.id)
        else:
            builder.add_edge(prev_name, agent.id)
        prev_name = agent.id
    builder.add_edge(prev_name, END)
    return builder.compile()


GRAPH = _build_graph()


# AC-4: surface agent disagreements instead of silently merging them. One
# rule today — AG-5 (capacity-aware shelter allocation) vs AG-6
# (distance-only routing) are the one pair that can genuinely target the same
# resource; a different-shelter answer means evacuees would be sent somewhere
# AG-5 already ruled out (e.g. full), so a human must reconcile it. Table is
# intentionally small; append future rules here rather than building a DSL.
CONFLICT_RULES = [
    {
        "agents": ("AG-5", "AG-6"),
        "target": "evacuation_shelter",
        "paths": (("details", "shelter", "id"), ("details", "destination", "id")),
        "template": "AG-5 allocates evacuees to shelter {a} (capacity-aware) "
                     "but AG-6 routes them to shelter {b} (distance-only) — "
                     "human must reconcile.",
    },
]


def _get_path(d: dict, path: tuple[str, ...]):
    cur = d
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _detect_conflicts(state: dict) -> list[dict]:
    conflicts = []
    for rule in CONFLICT_RULES:
        a_id, b_id = rule["agents"]
        a_rec, b_rec = state.get(a_id), state.get(b_id)
        if not a_rec or not b_rec:
            continue
        a_val = _get_path(a_rec, rule["paths"][0])
        b_val = _get_path(b_rec, rule["paths"][1])
        if not a_val or not b_val or a_val == b_val:
            continue
        conflicts.append({
            "agents": [a_id, b_id],
            "target": rule["target"],
            "values": {a_id: a_val, b_id: b_val},
            "recs": [a_rec["rec_id"], b_rec["rec_id"]],
            "created_at": {a_id: a_rec.get("created_at"), b_id: b_rec.get("created_at")},
            "rationale": rule["template"].format(a=a_val, b=b_val),
        })
    return conflicts


def run(incident_id: str, events: list[Event]) -> list[dict]:
    result = GRAPH.invoke({"incident_id": incident_id, "events": events, "recs": []})
    conflicts = _detect_conflicts(blackboard.get(incident_id))
    blackboard.merge(incident_id, {"conflicts": conflicts})
    return result["recs"]
