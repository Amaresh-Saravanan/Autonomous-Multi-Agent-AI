from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.citizen_assistance.agent import ChatRequest, CitizenAssistant
from app.agents.damage_assessment.agent import DamageAssessmentAgent
from app.agents.disaster_assessment.agent import DisasterAssessmentAgent
from app.agents.medical_coordination.agent import MedicalCoordinationAgent
from app.agents.resource_allocation.agent import ResourceAllocationAgent
from app.agents.route_optimization.agent import RouteOptimizationAgent
from app.agents.rescue_planning.agent import RescuePlanningAgent
from app.agents.situational_intelligence.agent import SituationalIntelligenceAgent
from app.infrastructure.llm import LLMService
from app.models.agent import AgentStatusEnum
from app.models.incident import LocationStateEnum

RESOURCES = {
    "teams": [{"id": "t-1", "name": "Alpha", "lat": 13.06, "lon": 80.27, "status": "available"}],
    "hospitals": [{"id": "h-1", "name": "Coastal General", "lat": 13.05, "lon": 80.28, "free_beds": 8}],
    "ambulances": [{"id": "amb-1", "lat": 13.05, "lon": 80.28, "status": "available"}],
    "shelters": [{"id": "s-1", "name": "Community Hall", "lat": 13.07, "lon": 80.26, "capacity": 300, "occupied": 100}],
    "supplies": {"food_units": 5000, "water_liters": 20000, "blankets": 1500},
}


def _known_location_context(**overrides) -> AgentContext:
    base = dict(
        incident_id="inc-1",
        source_type="iot",
        severity=0.8,
        location_state=LocationStateEnum.EXACT,
        latitude=13.08,
        longitude=80.27,
        resources=RESOURCES,
        blackboard={"AG-1": {"severity": 0.8, "evidence": ["evt-1"]}, "AG-2": {"details": {"affected_population": 100}, "evidence": ["evt-1"]}},
    )
    base.update(overrides)
    return AgentContext(**base)


def test_ag1_no_events_monitors():
    agent = DisasterAssessmentAgent()
    result = agent.run(AgentContext(incident_id="inc-1"))
    assert result.status == AgentStatusEnum.SUCCESS
    assert result.recommendations[0]["action"] == "monitor"


def test_ag1_threshold_raises_severity_above_critical():
    agent = DisasterAssessmentAgent()
    context = AgentContext(
        incident_id="inc-1",
        events=[{"event_id": "evt-1", "source_type": "iot", "payload": {"metric": "water_level", "reading": 5.5, "unit": "m"}}],
        evidence_event_ids=["evt-1"],
    )
    result = agent.run(context)
    assert result.status == AgentStatusEnum.SUCCESS
    assert result.recommendations[0]["action"] == "raise_severity"
    assert result.fallback_used is False


def test_ag1_llm_failure_is_degraded_not_disguised_as_success():
    class FailingLLM(LLMService):
        def __init__(self):
            super().__init__(client=object(), model="m", provider_name="p")

        def reason(self, prompt, max_tokens=256):
            from app.infrastructure.llm import LLMResult

            return LLMResult(status="DEGRADED", reasoning_mode="deterministic_fallback", fallback_used=True,
                              fallback_reason="timeout", latency_ms=1.0, model="m", provider="p")

    agent = DisasterAssessmentAgent()
    context = AgentContext(
        incident_id="inc-1",
        events=[{"event_id": "evt-1", "source_type": "iot", "payload": {"metric": "water_level", "reading": 5.5}}],
        llm=FailingLLM(),
    )
    result = agent.run(context)
    assert result.status == AgentStatusEnum.DEGRADED
    assert result.fallback_used is True
    assert result.metadata["fallback_reason"] == "timeout"


def test_ag2_labels_itself_a_heuristic_not_real_imagery():
    agent = DamageAssessmentAgent()
    result = agent.run(_known_location_context())
    assert "heuristic" in result.reasoning.lower()
    assert "NOT imagery" in result.reasoning


def test_ag3_dispatches_nearest_available_team():
    agent = RescuePlanningAgent()
    result = agent.run(_known_location_context())
    assert result.recommendations[0]["action"] == "dispatch:t-1"


def test_ag3_unknown_location_never_invents_coordinates():
    agent = RescuePlanningAgent()
    context = _known_location_context(location_state=LocationStateEnum.UNKNOWN, latitude=None, longitude=None)
    result = agent.run(context)
    assert result.status == AgentStatusEnum.DEGRADED
    assert result.recommendations[0]["action"] == "escalate:location_unavailable"


def test_ag4_allocates_hospital_with_free_beds():
    agent = MedicalCoordinationAgent()
    result = agent.run(_known_location_context())
    assert result.recommendations[0]["action"] == "allocate:h-1"


def test_ag5_allocates_nearest_open_shelter():
    agent = ResourceAllocationAgent()
    result = agent.run(_known_location_context())
    assert result.recommendations[0]["action"] == "allocate_shelter:s-1"


def test_ag6_routes_to_nearest_shelter_unblocked():
    agent = RouteOptimizationAgent()
    result = agent.run(_known_location_context())
    assert result.recommendations[0]["action"] == "route:s-1"
    assert result.metadata["provider"] == "straight_line_fallback"


def test_ag6_flags_blocked_segment():
    """Origin and destination straddle the hardcoded blocked segment at
    (13.06, 80.265) — their midpoint lands within its 0.5km radius."""
    agent = RouteOptimizationAgent()
    context = _known_location_context(
        latitude=13.06, longitude=80.263,
        resources={**RESOURCES, "shelters": [{"id": "s-1", "name": "Near Shelter", "lat": 13.06, "lon": 80.267, "capacity": 10, "occupied": 0}]},
    )
    result = agent.run(context)
    assert result.recommendations[0]["action"] == "route:detour_required"


def test_ag7_retrieval_fallback_answers_flood_query():
    assistant = CitizenAssistant()
    response = assistant.chat(ChatRequest(message="the water is rising, what should I do?"))
    assert response.reasoning_mode == "retrieval_fallback"
    assert "evacuate" in response.reply.lower()


def test_ag7_says_information_unavailable_when_nothing_matches():
    assistant = CitizenAssistant()
    response = assistant.chat(ChatRequest(message="xyzzy qwerty unmatched gibberish"))
    assert response.reasoning_mode == "unavailable"
    assert "not available" in response.reply.lower()


def test_run_catches_execute_exception_and_returns_failed_result():
    """Phase 23: one agent's exception must not propagate out of run()."""

    class CrashingAgent(BaseAgent):
        id = "AG-X"

        def execute(self, context: AgentContext) -> AgentResult:
            raise RuntimeError("simulated crash")

    result = CrashingAgent().run(AgentContext(incident_id="inc-1"))
    assert result.status == AgentStatusEnum.FAILED
    assert result.fallback_used is True
    assert result.errors == ["simulated crash"]
    assert result.evidence  # validate_explainable() requires non-empty evidence
    assert result.reasoning  # and non-empty rationale


def test_ag8_summarizes_blackboard_without_citing_itself():
    agent = SituationalIntelligenceAgent()
    context = AgentContext(
        incident_id="inc-1",
        blackboard={"AG-1": {"severity": 0.9, "action": "raise_severity"}, "AG-5": {"severity": 0.0, "action": "allocate_shelter:s-1"}},
    )
    result = agent.run(context)
    assert result.status == AgentStatusEnum.SUCCESS
    assert "AG-8" not in result.evidence
    assert set(result.evidence) == {"AG-1", "AG-5"}
    assert result.recommendations[0]["severity"] == 0.9


def test_ag7_answers_in_hindi_and_tamil_without_llm():
    assistant = CitizenAssistant()
    hi = assistant.chat(ChatRequest(message="पानी बढ़ रहा है, क्या करूँ?", language="hi"))
    assert hi.reasoning_mode == "retrieval_fallback" and hi.language == "hi" and not hi.language_fallback
    assert hi.sources == ["flood-evacuate"] and "ऊँची जगह" in hi.reply
    ta = assistant.chat(ChatRequest(message="வெள்ளம் வருகிறது என்ன செய்வது", language="ta"))
    assert ta.language == "ta" and ta.sources == ["flood-evacuate"] and not ta.language_fallback
    bleeding = assistant.chat(ChatRequest(message="बहुत खून बह रहा है", language="hi"))
    assert bleeding.sources == ["first-aid-bleeding"]


def test_ag7_localized_unavailable_and_honest_language_fallback():
    assistant = CitizenAssistant()
    none_hi = assistant.chat(ChatRequest(message="अरे ब्ला ब्ला", language="hi"))
    assert none_hi.reasoning_mode == "unavailable" and none_hi.language == "hi" and "उपलब्ध नहीं" in none_hi.reply
    # English typed while UI is Hindi -> English answer, flagged as fallback.
    mixed = assistant.chat(ChatRequest(message="the water is rising", language="hi"))
    assert mixed.language == "en" and mixed.language_fallback
    # Telugu has no corpus and no LLM: English reply, flagged.
    te = assistant.chat(ChatRequest(message="the water is rising", language="te"))
    assert te.language == "en" and te.language_fallback
    te_none = assistant.chat(ChatRequest(message="xyzzy qwerty", language="te"))
    assert te_none.reasoning_mode == "unavailable" and te_none.language_fallback
