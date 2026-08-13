"""Trigger-based agent scheduling (tracker 2.1): agents only run when
relevant event types are present in the batch.

Note: backend/app/normalizers.py only registers normalizers for 'iot',
'weather', and 'satellite' today, so this feature is forward-looking — no
current /ingest/* call can actually trigger an agent skip today. But the
unit-level tests below verify the mechanism, including with hypothetical
source_types (e.g. 'citizen') that no normalizer currently produces.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # backend/ on path

from app.models import Event, Geo
from app.orchestrator import _should_run


def _make_event(source_type="iot") -> Event:
    """Helper: construct a minimal Event for testing."""
    return Event(
        source_type=source_type,
        source_id="test-source",
        geo=Geo(type="Point", coordinates=[0.0, 0.0]),
    )


def test_should_run_always_run_agent_with_any_event():
    """AG-1 always runs, regardless of event source_type."""
    assert _should_run("AG-1", [_make_event(source_type="weather")]) is True
    assert _should_run("AG-1", [_make_event(source_type="citizen")]) is True
    assert _should_run("AG-1", [_make_event(source_type="unknown")]) is True


def test_should_run_always_run_agent_with_empty_events():
    """AG-1 always runs, even with no events."""
    assert _should_run("AG-1", []) is True


def test_should_run_always_run_agent_ag2_with_any_event():
    """AG-2 always runs (pure function of AG-1's output, not event payload)."""
    assert _should_run("AG-2", [_make_event(source_type="weather")]) is True
    assert _should_run("AG-2", [_make_event(source_type="citizen")]) is True


def test_should_run_always_run_agent_ag8_with_any_event():
    """AG-8 always runs (summarizes full blackboard)."""
    assert _should_run("AG-8", [_make_event(source_type="weather")]) is True
    assert _should_run("AG-8", [_make_event(source_type="citizen")]) is True


def test_should_run_filtered_agent_skips_irrelevant_event():
    """AG-3 skips when event source_type is not in its relevance set."""
    assert _should_run("AG-3", [_make_event(source_type="citizen")]) is False
    assert _should_run("AG-3", [_make_event(source_type="social")]) is False
    assert _should_run("AG-3", [_make_event(source_type="gis")]) is False


def test_should_run_filtered_agent_runs_on_relevant_event():
    """AG-3 runs when event source_type is in its relevance set."""
    assert _should_run("AG-3", [_make_event(source_type="iot")]) is True
    assert _should_run("AG-3", [_make_event(source_type="satellite")]) is True
    assert _should_run("AG-3", [_make_event(source_type="weather")]) is True


def test_should_run_ag4_filtered_events():
    """AG-4 has same relevance set as AG-3."""
    assert _should_run("AG-4", [_make_event(source_type="iot")]) is True
    assert _should_run("AG-4", [_make_event(source_type="citizen")]) is False


def test_should_run_ag5_filtered_events():
    """AG-5 has same relevance set as AG-3."""
    assert _should_run("AG-5", [_make_event(source_type="satellite")]) is True
    assert _should_run("AG-5", [_make_event(source_type="social")]) is False


def test_should_run_ag6_filtered_events():
    """AG-6 has same relevance set as AG-3."""
    assert _should_run("AG-6", [_make_event(source_type="weather")]) is True
    assert _should_run("AG-6", [_make_event(source_type="gis")]) is False


def test_should_run_multiple_events_any_match():
    """If any event in the batch matches relevance set, agent runs."""
    events = [
        _make_event(source_type="citizen"),    # not relevant
        _make_event(source_type="social"),     # not relevant
        _make_event(source_type="iot"),        # relevant
    ]
    assert _should_run("AG-3", events) is True


def test_should_run_multiple_events_none_match():
    """If no events in the batch match relevance set, agent skips."""
    events = [
        _make_event(source_type="citizen"),
        _make_event(source_type="social"),
    ]
    assert _should_run("AG-3", events) is False


def test_should_run_unknown_agent_defaults_to_true():
    """Unknown agent IDs (not in AGENT_EVENT_TYPES) default to always run."""
    assert _should_run("AG-99", [_make_event(source_type="citizen")]) is True
