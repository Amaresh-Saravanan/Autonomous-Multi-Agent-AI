"""Unit tests for AG-8 (Situational Intelligence) and the DS-1 severity grid
(tracker 1.12 — the two Phase 1 items that had zero direct coverage).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from agents.situational import SituationalIntelligenceAgent
from app import severity_grid, geo_utils

ag8 = SituationalIntelligenceAgent()


def test_ag8_empty_blackboard_returns_valid_recommendation():
    rec = ag8.run("inc-1", [], state={})
    rec.validate_explainable()  # must not raise
    assert rec.action == "summarize"
    assert rec.severity == 0.0


def test_ag8_aggregates_max_severity_across_agents():
    state = {
        "AG-1": {"severity": 0.3, "action": "monitor"},
        "AG-3": {"severity": 0.9, "action": "dispatch_team"},
    }
    rec = ag8.run("inc-1", [], state=state)
    rec.validate_explainable()
    assert rec.severity == 0.9
    assert set(rec.evidence) == {"AG-1", "AG-3"}


def test_ag8_ignores_its_own_prior_output():
    state = {
        "AG-1": {"severity": 0.4, "action": "monitor"},
        "AG-8": {"severity": 0.4, "action": "summarize"},
    }
    rec = ag8.run("inc-1", [], state=state)
    assert "AG-8" not in rec.evidence


def test_cell_id_quantizes_to_grid_precision():
    assert geo_utils.cell_id(13.0827, 80.2707) == geo_utils.cell_id(13.084, 80.271)


def test_severity_grid_keeps_worst_case_per_cell():
    severity_grid.update("inc-grid", 13.08, 80.27, 0.3)
    severity_grid.update("inc-grid", 13.0801, 80.2701, 0.8)  # same cell, higher
    severity_grid.update("inc-grid", 13.0802, 80.2702, 0.5)  # same cell, lower
    geojson = severity_grid.as_geojson("inc-grid")
    assert len(geojson["features"]) == 1
    assert geojson["features"][0]["properties"]["severity"] == 0.8


def test_severity_grid_geojson_is_valid_polygon_per_cell():
    severity_grid.update("inc-grid-2", 13.0, 80.0, 0.6)
    geojson = severity_grid.as_geojson("inc-grid-2")
    feature = geojson["features"][0]
    assert feature["geometry"]["type"] == "Polygon"
    ring = feature["geometry"]["coordinates"][0]
    assert ring[0] == ring[-1]  # closed ring
    assert len(ring) == 5


if __name__ == "__main__":
    test_ag8_empty_blackboard_returns_valid_recommendation()
    test_ag8_aggregates_max_severity_across_agents()
    test_ag8_ignores_its_own_prior_output()
    test_cell_id_quantizes_to_grid_precision()
    test_severity_grid_keeps_worst_case_per_cell()
    test_severity_grid_geojson_is_valid_polygon_per_cell()
    print("OK: AG-8 + severity grid unit tests passed.")
