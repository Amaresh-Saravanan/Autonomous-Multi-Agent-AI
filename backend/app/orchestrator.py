"""Agent orchestration via LangGraph (TDD 4.3, tracker 2.1).

Graph nodes = agents, chained in the existing data-dependency order
(AG-1 defines the incident; AG-8 summarizes last). Each node performs the
same side effects the old main.py loop did: refresh blackboard state, run
the agent, merge its output back into the blackboard, record the
recommendation, and (for AG-1) update the severity grid.

ponytail: trigger-based selective scheduling (only running agents relevant
to an event type) is NOT implemented here — every agent still runs on every
event, same as before this module existed. Add that when tracker 2.1's
"trigger routing" half is picked up.
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


def _detect_conflicts(state: dict) -> list[dict]:
    """AC-4: surface disagreements instead of silently merging them.

    AG-5 (capacity-aware shelter allocation) and AG-6 (distance-only routing)
    are the one pair that can genuinely target the same resource — a
    different-shelter answer means evacuees would be sent somewhere AG-5
    already ruled out (e.g. full), so a human must reconcile it.
    """
    ag5_shelter = state.get("AG-5", {}).get("details", {}).get("shelter", {}).get("id")
    ag6_dest = state.get("AG-6", {}).get("details", {}).get("destination", {}).get("id")
    if not ag5_shelter or not ag6_dest or ag5_shelter == ag6_dest:
        return []
    return [{
        "agents": ["AG-5", "AG-6"],
        "target": "evacuation_shelter",
        "values": {"AG-5": ag5_shelter, "AG-6": ag6_dest},
        "recs": [state["AG-5"]["rec_id"], state["AG-6"]["rec_id"]],
        "rationale": (
            f"AG-5 allocates evacuees to shelter {ag5_shelter} (capacity-aware) "
            f"but AG-6 routes them to shelter {ag6_dest} (distance-only) — "
            "human must reconcile."
        ),
    }]


def run(incident_id: str, events: list[Event]) -> list[dict]:
    result = GRAPH.invoke({"incident_id": incident_id, "events": events, "recs": []})
    conflicts = _detect_conflicts(blackboard.get(incident_id))
    blackboard.merge(incident_id, {"conflicts": conflicts})
    return result["recs"]
