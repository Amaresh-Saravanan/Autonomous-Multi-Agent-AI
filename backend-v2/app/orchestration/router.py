"""Agent router (Phase 16). Fixed data-dependency order (AG-1 defines the
incident; AG-8 summarizes last) — same order as V1, but which agents
actually run is decided by `conditions.should_run`, not just `triggers`.
AG-7 (citizen chat) is intentionally excluded: it's invoked directly from
`api/citizen.py`, not event-triggered (see CLAUDE.md)."""

from app.agents.base import BaseAgent
from app.agents.damage_assessment.agent import DamageAssessmentAgent
from app.agents.disaster_assessment.agent import DisasterAssessmentAgent
from app.agents.medical_coordination.agent import MedicalCoordinationAgent
from app.agents.resource_allocation.agent import ResourceAllocationAgent
from app.agents.rescue_planning.agent import RescuePlanningAgent
from app.agents.route_optimization.agent import RouteOptimizationAgent
from app.agents.situational_intelligence.agent import SituationalIntelligenceAgent

AGENT_CHAIN: list[BaseAgent] = [
    DisasterAssessmentAgent(),
    DamageAssessmentAgent(),
    RescuePlanningAgent(),
    MedicalCoordinationAgent(),
    ResourceAllocationAgent(),
    RouteOptimizationAgent(),
    SituationalIntelligenceAgent(),
]
