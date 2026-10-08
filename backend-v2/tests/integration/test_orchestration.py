import fakeredis

from app.incidents.service import IncidentService
from app.models.agent import AgentHealth
from app.models.incident import Event, LocationStateEnum
from app.models.recommendation import Recommendation
from app.models.resource import Hospital, RescueTeam, Resource, Shelter
from app.models.security import Agency
from app.orchestration.graph import run_for_event
from app.orchestration.state import BlackboardService
from datetime import datetime, timezone


def _seed_resources(db, agency_id):
    # s-1 is nearest to the incident but at full capacity; s-2 is farther but
    # open — AG-5 (capacity-aware) must diverge from AG-6 (distance-only),
    # reproducing the genuine AC-4 conflict V1 was built to surface.
    db.add_all([
        Shelter(name="Near Full Shelter", agency_id=agency_id, latitude=13.071, longitude=80.261, capacity=100, occupied=100),
        Shelter(name="Far Open Shelter", agency_id=agency_id, latitude=13.20, longitude=80.40, capacity=500, occupied=0),
        Hospital(name="General", agency_id=agency_id, latitude=13.05, longitude=80.28, beds_total=50, beds_free=10),
        RescueTeam(name="Alpha", agency_id=agency_id, latitude=13.06, longitude=80.27),
        Resource(name="Food", category="food_units", agency_id=agency_id, quantity=5000),
        Resource(name="Water", category="water_liters", agency_id=agency_id, quantity=20000),
        Resource(name="Blankets", category="blankets", agency_id=agency_id, quantity=1500),
    ])
    db.commit()


def test_full_chain_persists_recommendations_updates_severity_and_health(db):
    agency = Agency(name="Flood EOC", code="FEOC")
    db.add(agency)
    db.commit()
    _seed_resources(db, agency.id)

    incidents = IncidentService(db)
    incident = incidents.create(latitude=13.07, longitude=80.26, location_state=LocationStateEnum.EXACT)

    event = Event(
        incident_id=incident.id,
        source_type="iot",
        payload={"metric": "water_level", "reading": 5.5, "unit": "m"},
        location_state=LocationStateEnum.EXACT,
        latitude=13.07,
        longitude=80.26,
        received_at=datetime.now(timezone.utc),
    )
    db.add(event)
    db.commit()

    blackboard = BlackboardService(fakeredis.FakeStrictRedis(decode_responses=True))
    result = run_for_event(db, event.id, blackboard)

    recs = db.query(Recommendation).filter(Recommendation.incident_id == incident.id).all()
    rec_agents = {r.agent_id for r in recs}
    assert "AG-1" in rec_agents
    assert "AG-8" in rec_agents  # last agent in the chain always runs

    refreshed = incidents.get(incident.id)
    assert refreshed.severity > 0.0  # AG-1 raised it off the DETECTED default

    health_rows = db.query(AgentHealth).all()
    assert len(health_rows) >= 1
    assert all(h.execution_count >= 1 for h in health_rows)

    assert len(result["conflicts"]) == 1
    assert result["conflicts"][0]["category"] == "shelter_conflict"
