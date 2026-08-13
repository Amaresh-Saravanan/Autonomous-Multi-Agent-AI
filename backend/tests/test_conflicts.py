"""Conflict surfacing (tracker 2.2, PRD AC-4): AG-5 (capacity-aware shelter
allocation) and AG-6 (distance-only routing) can pick different shelters for
the same incident — that disagreement must be surfaced, not silently merged.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from fastapi.testclient import TestClient
from app.main import app
from app.orchestrator import _detect_conflicts
from _auth_helpers import viewer_headers

client = TestClient(app)


def _state(ag5_shelter=None, ag6_dest=None, ag5_rec_id="rec-5", ag6_rec_id="rec-6"):
    state = {}
    if ag5_shelter is not None:
        state["AG-5"] = {"rec_id": ag5_rec_id, "details": {"shelter": {"id": ag5_shelter}}}
    if ag6_dest is not None:
        state["AG-6"] = {"rec_id": ag6_rec_id, "details": {"destination": {"id": ag6_dest}}}
    return state


def test_same_shelter_choice_is_no_conflict():
    state = _state(ag5_shelter="s-1", ag6_dest="s-1")
    assert _detect_conflicts(state) == []


def test_different_shelter_choice_is_a_conflict():
    state = _state(ag5_shelter="s-2", ag6_dest="s-1")
    conflicts = _detect_conflicts(state)
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict["agents"] == ["AG-5", "AG-6"]
    assert conflict["values"] == {"AG-5": "s-2", "AG-6": "s-1"}
    assert conflict["recs"] == ["rec-5", "rec-6"]


def test_missing_agent_output_is_no_conflict():
    assert _detect_conflicts({}) == []
    assert _detect_conflicts(_state(ag5_shelter="s-1")) == []


def test_escalated_recommendation_without_shelter_is_no_conflict():
    state = {
        "AG-5": {"rec_id": "rec-5", "details": {}},
        "AG-6": {"rec_id": "rec-6", "details": {"destination": {"id": "s-1"}}},
    }
    assert _detect_conflicts(state) == []


def test_real_ingest_surfaces_shelter_conflict_via_incident_endpoint():
    """s-1 (nearest shelter) is seeded full — AG-5 diverts to s-2, AG-6 still
    routes to s-1 — so a real /ingest call must produce a conflict visible
    through the existing GET /incidents/{id} endpoint (AC-4: pull-only)."""
    r = client.post("/ingest/iot", json={
        "sensor_id": "wl-conflict-1", "metric": "water_level",
        "reading": 6.0, "unit": "m",
        "lat": 13.07, "lon": 80.26,  # s-1's own coords: unambiguously nearest
        "incident_id": "conflict-scenario-1",
    })
    assert r.status_code == 200

    state = client.get("/incidents/conflict-scenario-1", headers=viewer_headers()).json()
    assert len(state["conflicts"]) == 1
    conflict = state["conflicts"][0]
    assert conflict["agents"] == ["AG-5", "AG-6"]
    assert conflict["values"] == {"AG-5": "s-2", "AG-6": "s-1"}
