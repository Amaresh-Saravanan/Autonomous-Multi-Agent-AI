# LangGraph Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fixed Python `for` loop in `backend/app/main.py` that runs all 7 agents with a LangGraph `StateGraph`, preserving identical behavior (tracker item 2.1).

**Architecture:** New `backend/app/orchestrator.py` owns the agent list and a compiled `StateGraph` with one node per agent, chained in the existing dependency order (AG-1 → AG-2 → AG-3 → AG-4 → AG-5 → AG-6 → AG-8). Each node performs the same side effects the current loop body performs (blackboard merge, recommendation recording, severity grid update). `main.py`'s `/ingest` handler calls `orchestrator.run(incident_id, events)` instead of looping itself.

**Tech Stack:** Python 3.11, FastAPI, `langgraph` (new dependency), pytest.

## Global Constraints

- Behavior must be identical to today: same 7 agents, same order, same `/ingest` response shape, same blackboard/recommendation/severity-grid side effects.
- No trigger-based selective agent scheduling in this plan (separate tracker item).
- No conflict surfacing / `conflicts[]` (tracker 2.2, separate item).
- No new test file — the existing 15-test suite (`backend/tests/`) is the regression gate. Baseline today: `15 passed` (confirmed via `python -m pytest tests/ -v` in `backend/`).
- Full spec: `docs/superpowers/specs/2026-08-10-langgraph-orchestrator-design.md`.

---

### Task 1: Add `langgraph` dependency and create the orchestrator module

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/orchestrator.py`

**Interfaces:**
- Produces: `orchestrator.run(incident_id: str, events: list[Event]) -> list[dict]` — runs all 7 agents in order, returns the list of recommendation dicts (same shape as today's `recs` list in `main.py`).
- Consumes: `agents.disaster.DisasterAssessmentAgent`, `agents.damage.DamageAssessmentAgent`, `agents.rescue.RescuePlanningAgent`, `agents.medical.MedicalCoordinationAgent`, `agents.allocation.ResourceAllocationAgent`, `agents.route.RouteOptimizationAgent`, `agents.situational.SituationalIntelligenceAgent` (each has `.id: str` and `.run(incident_id, events, state) -> Recommendation`, per `backend/agents/base.py`). Also `app.blackboard.get`/`.merge`, `app.recommendations.record`, `app.severity_grid.update`, `app.models.Event`.

- [ ] **Step 1: Confirm baseline test suite is green**

Run: `cd backend && python -m pytest tests/ -v`
Expected: `15 passed` (this is the pre-change baseline — if it's not 15 passed, stop and investigate before proceeding, don't build on a broken baseline).

- [ ] **Step 2: Add `langgraph` to requirements and install it**

Edit `backend/requirements.txt` to add one line at the end:

```
langgraph
```

Run: `cd backend && python -m pip install -r requirements.txt -q`
Expected: no errors; `langgraph` installs (pulls in `langgraph`, `langgraph-checkpoint`, etc. as transitive deps — that's normal).

- [ ] **Step 3: Write `backend/app/orchestrator.py`**

```python
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


def run(incident_id: str, events: list[Event]) -> list[dict]:
    result = GRAPH.invoke({"incident_id": incident_id, "events": events, "recs": []})
    return result["recs"]
```

- [ ] **Step 4: Sanity-check the module imports and compiles**

Run: `cd backend && python -c "from app import orchestrator; print(len(orchestrator.AGENTS), 'agents wired')"`
Expected: `7 agents wired` with no traceback.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/orchestrator.py
git commit -m "Add LangGraph orchestrator module (not yet wired into main.py)"
```

---

### Task 2: Wire `/ingest` through the orchestrator and retire the old loop

**Files:**
- Modify: `backend/app/main.py:1-73` (imports, `AGENTS` list, and the `/ingest` handler body)
- Modify: `docs/MIGRATION_TRACKER.md:66` (mark 2.1 done)

**Interfaces:**
- Consumes: `orchestrator.run(incident_id: str, events: list[Event]) -> list[dict]` (from Task 1).

- [ ] **Step 1: Replace the agent imports, `AGENTS` list, and `/ingest` loop in `main.py`**

Current `main.py` (lines 1–73) looks like this:

```python
from __future__ import annotations

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import audit
from . import blackboard
from . import recommendations
from . import severity_grid
from .normalizers import normalize
from agents.disaster import DisasterAssessmentAgent
from agents.damage import DamageAssessmentAgent
from agents.rescue import RescuePlanningAgent
from agents.medical import MedicalCoordinationAgent
from agents.allocation import ResourceAllocationAgent
from agents.route import RouteOptimizationAgent
from agents.situational import SituationalIntelligenceAgent
from agents import citizen as citizen_agent

app = FastAPI(title="Disaster Response Platform - Phase 2 slice")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# ponytail: order = data dependency chain (TDD 4.3). Each agent reads
# upstream agents' blackboard output; AG-8 summarizes everything last.
AGENTS = [
    DisasterAssessmentAgent(),
    DamageAssessmentAgent(),
    RescuePlanningAgent(),
    MedicalCoordinationAgent(),
    ResourceAllocationAgent(),
    RouteOptimizationAgent(),
    SituationalIntelligenceAgent(),
]
_ws_clients: list[WebSocket] = []


@app.get("/health")
def health():
    return {"status": "ok", "using_redis": blackboard.using_redis()}


@app.post("/ingest/{source_type}")
async def ingest(source_type: str, raw: dict):
    event = normalize(source_type, raw)
    incident_id = raw.get("incident_id", "default")

    recs = []
    for agent in AGENTS:
        state = blackboard.get(incident_id)  # refresh state after each agent
        rec = agent.run(incident_id, [event], state)
        rec_dict = rec.model_dump()
        recs.append(rec_dict)
        blackboard.merge(incident_id, {agent.id: rec_dict})
        recommendations.record(rec_dict)
        # DS-1 severity heat-map (tracker 1.5): AG-1 defines disaster severity.
        if agent.id == "AG-1" and rec.geo.type == "Point" and len(rec.geo.coordinates) == 2:
            lon, lat = rec.geo.coordinates
            severity_grid.update(incident_id, lat, lon, rec.severity)

    for client in list(_ws_clients):
        try:
            await client.send_json({"incident_id": incident_id, "recommendations": recs})
        except Exception:  # noqa: BLE001 - drop dead clients
            _ws_clients.remove(client)

    return {"event_id": event.event_id, "incident_id": incident_id, "recommendations": recs}
```

Replace it with:

```python
from __future__ import annotations

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import audit
from . import blackboard
from . import orchestrator
from . import recommendations
from . import severity_grid
from .normalizers import normalize
from agents import citizen as citizen_agent

app = FastAPI(title="Disaster Response Platform - Phase 2 slice")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_ws_clients: list[WebSocket] = []


@app.get("/health")
def health():
    return {"status": "ok", "using_redis": blackboard.using_redis()}


@app.post("/ingest/{source_type}")
async def ingest(source_type: str, raw: dict):
    event = normalize(source_type, raw)
    incident_id = raw.get("incident_id", "default")

    recs = orchestrator.run(incident_id, [event])

    for client in list(_ws_clients):
        try:
            await client.send_json({"incident_id": incident_id, "recommendations": recs})
        except Exception:  # noqa: BLE001 - drop dead clients
            _ws_clients.remove(client)

    return {"event_id": event.event_id, "incident_id": incident_id, "recommendations": recs}
```

Everything below `/ingest` in `main.py` (the `/incidents/{incident_id}` route through the end of the file) is untouched — leave it exactly as is. Note the `severity_grid` import stays in `main.py`'s top-of-file imports (shown above) because the existing `get_severity_grid` route (`main.py:82-84`) calls `severity_grid.as_geojson(...)` directly — only the *update* call moves into `orchestrator.py`, the import itself is still needed here.

- [ ] **Step 2: Run the full test suite — this is the regression gate**

Run: `cd backend && python -m pytest tests/ -v`
Expected: `15 passed` — identical to the Task 1 Step 1 baseline. If any test fails, the refactor changed behavior; diff the failing test's assertion against what `orchestrator.py`'s node function does and fix the node function (not the test — the test encodes the spec).

- [ ] **Step 3: Mark tracker item 2.1 done**

In `docs/MIGRATION_TRACKER.md`, change line 66 from:

```
| 2.1 | LangGraph orchestrator (trigger routing, agent scheduling) | P0 | ☐ | current: simple ordered list in main.py, not LangGraph yet |
```

to:

```
| 2.1 | LangGraph orchestrator (trigger routing, agent scheduling) | P0 | ◐ | agent scheduling done via app/orchestrator.py (StateGraph, fixed order) — trigger routing (selective agent scheduling) still deferred |
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py docs/MIGRATION_TRACKER.md
git commit -m "Wire /ingest through LangGraph orchestrator (tracker 2.1)"
```
