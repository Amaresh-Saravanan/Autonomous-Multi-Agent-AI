# LangGraph Orchestrator — Design

**Date:** 2026-08-10
**Tracker item:** 2.1 (`docs/MIGRATION_TRACKER.md`)
**Status:** approved

## Problem

`backend/app/main.py` currently runs all 7 agents on every `/ingest` call via a
plain Python `for` loop over a module-level `AGENTS` list, with per-agent
bookkeeping (blackboard merge, recommendation recording, severity grid update)
inlined in the loop body. TDD 4.3 specifies LangGraph as the orchestration
layer (graph nodes = agents, edges = data dependencies). The tracker flags
this as not yet done.

## Scope

1:1 behavioral port only:
- Same 7 agents (AG-1, AG-2, AG-3, AG-4, AG-5, AG-6, AG-8), same fixed
  execution order, same side effects, same `/ingest` response shape.
- **Out of scope** (separate tracker items, not touched here):
  - 2.1's "trigger routing" half — no per-agent `triggers()` filtering; every
    agent still runs on every event, as today.
  - 2.2 conflict surfacing (`conflicts[]`, AC-4) — not implemented.

## Design

### New file: `backend/app/orchestrator.py`

- Owns the `AGENTS` list (moved out of `main.py`).
- Graph state (`TypedDict`): `{incident_id: str, events: list[Event], recs: list[dict]}`.
- One `StateGraph` node per agent, chained in the existing dependency order
  via `add_edge` (AG-1 → AG-2 → AG-3 → AG-4 → AG-5 → AG-6 → AG-8 → END).
  Entry point is AG-1.
- Each node function replicates exactly what `main.py`'s loop body does today:
  1. `blackboard.get(incident_id)` — refresh state after prior agents.
  2. `agent.run(incident_id, events, state)`.
  3. `blackboard.merge(incident_id, {agent.id: rec_dict})`.
  4. `recommendations.record(rec_dict)`.
  5. If `agent.id == "AG-1"` and geo is a Point, `severity_grid.update(...)`.
  6. Append `rec_dict` to `state["recs"]`, return updated state.
- Graph compiled once at module import time (`orchestrator.GRAPH = builder.compile()`).
- Public function: `run(incident_id: str, events: list[Event]) -> list[dict]`
  — invokes the compiled graph, returns `state["recs"]`.

### `backend/app/main.py` changes

`/ingest` handler shrinks to: normalize event → `orchestrator.run(incident_id, [event])`
→ WS push the returned recs → return response. All per-agent bookkeeping is
removed from `main.py` (now lives in `orchestrator.py`).

### `backend/requirements.txt`

Add `langgraph`.

## Error handling

Unchanged. If an agent raises, propagation behavior matches today (ingest
fails). No new failure modes introduced by this refactor.

## Testing

No new test file — this is a refactor, not a feature. Existing suite must
pass unmodified as the regression check:
- `tests/test_slice.py`
- `tests/test_agents.py`
- `tests/test_scenario.py`
- `tests/test_recommendations.py`

These assert on `/ingest` response shape and blackboard/recommendation state,
not on the internal call mechanism, so they're valid regression coverage for
a pure orchestration-layer swap.
