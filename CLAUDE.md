# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Autonomous multi-agent disaster-response platform. Synthetic/real sensor events flow through normalizers → a chain of AI agents (rule-based with optional LLM reasoning) → recommendations with mandatory evidence/rationale → a live map dashboard, over HTTP + WebSocket. Currently mid-way through Phase 2 of `docs/MIGRATION_TRACKER.md` (see that file for what's shipped vs. deferred — it's the source of truth, more current than the README).

Design docs, read in this order for full context: `docs/PRD.md` (requirements/goals), `docs/TDD.md` (architecture/stack), `docs/UX_DESIGN.md` (dashboard design), `docs/MIGRATION_TRACKER.md` (phase-by-phase build status + decisions log).

## Commands

Run from `backend/`:

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload      # start API on :8000
python -m pytest tests/ -v                    # all tests
python -m pytest tests/test_slice.py -v       # single test file
python -m pytest tests/test_slice.py::test_name -v   # single test
```

Frontend is a Next.js + TypeScript + Tailwind app in `frontend-next/` (`npm install && npm run dev`, serves on `localhost:3000`, connects to `localhost:8000`). The original Phase 0 `frontend/index.html` shell has been retired.

LLM reasoning is optional — set `GROQ_API_KEY` before starting uvicorn to enable it; everything falls back to rule-based logic without it (see `app/llm.py`).

## Architecture

**Request flow:** `POST /ingest/{source_type}` (`app/main.py`) → `normalizers.normalize()` converts the raw payload into a common `Event` (`app/models.py`) → `orchestrator.run()` invokes every agent in a fixed LangGraph `StateGraph` chain → each agent reads the shared blackboard, produces one `Recommendation`, and the orchestrator merges it back into the blackboard, records it, and (for AG-1) updates the severity grid → the full recommendation list is pushed to all connected `/ws/alerts` WebSocket clients and returned in the HTTP response.

**Agent contract** (`agents/base.py`): every agent is a class with `run(incident_id, events, state) -> Recommendation`. A `Recommendation` (`app/models.py`) *must* carry non-empty `evidence` (source event IDs) and `rationale` — `validate_explainable()` is the one enforcement point for the platform's core "every recommendation is explainable" requirement (PRD AC-3/DS-7). Don't add an agent output path that bypasses this.

**Orchestration** (`app/orchestrator.py`): agents run in a fixed sequence (AG-1 Disaster → AG-2 Damage → AG-3 Rescue → AG-4 Medical → AG-5 Allocation → AG-6 Route → AG-8 Situational), each agent id is a graph node, edges are just "run next." Every agent runs on every event — there's no trigger-based selective scheduling yet (tracker 2.1 notes this as a known gap). AG-1 runs first because it defines the incident; AG-8 runs last because it summarizes the whole blackboard.

**Blackboard** (`app/blackboard.py`): shared state keyed by `incident_id`, one dict per incident with each agent's latest output under its agent id. In-memory dict by default; switches to Redis automatically if `REDIS_URL` is set and reachable, with silent fallback to in-memory on any connection failure. No code should assume Redis is present.

**Agents** live in `backend/agents/`, one file per agent (`disaster.py`, `damage.py`, `rescue.py`, `medical.py`, `allocation.py`, `route.py`, `situational.py`, `citizen.py`). AG-7 (citizen chat) is invoked directly from `app/main.py`'s `/citizen/chat` endpoint rather than through the orchestrator chain, since it's request/response, not event-triggered.

**LLM usage** (`app/llm.py`): a single Groq client wrapper (`reason(prompt)`), used optionally by agents for reasoning; every agent has a rule-based/threshold fallback so the whole slice runs with nothing but Python installed. Don't make any agent hard-depend on the LLM being available.

**Human-in-the-loop**: agents only ever recommend. `POST /recommendations/{id}/approve|reject` (`app/main.py` → `app/recommendations.py`) is how a human decision gets applied; it's audited via `app/audit.py`. When updating this, note that the blackboard is only overwritten with a decision if the recommendation is still the agent's *latest* one (stale approvals must not resurrect an older state) — see `_decide()` in `app/main.py`.

**Severity grid**: `app/geo_utils.py` does lat/lon rounding (geohash-lite quantization) for grid cells — deliberately not the `h3-py` library (see decisions log in `docs/MIGRATION_TRACKER.md`, 2026-07-28). `app/severity_grid.py` accumulates per-incident cell severities and serves them as GeoJSON via `GET /incidents/{id}/severity`.

## Git workflow

- After finishing each `docs/MIGRATION_TRACKER.md` item (not each full Phase), run the backend test suite (`python -m pytest tests/ -v` from `backend/`). If it's green, commit and push directly to `origin main` (local `master` tracks `origin/main`) **without asking for confirmation first**.
- If the suite fails, do not push — stop and surface the failure instead.
- This standing authorization covers routine tracker-item pushes only. It does not cover force-pushes, history rewrites, or pushing to any branch other than `main`.

## Conventions specific to this repo

- `ponytail:` comments mark a deliberate simplification with a known ceiling and an explicit upgrade trigger (e.g. straight-line routing instead of real OSRM in `agents/route.py`, fixed "operator" actor string instead of real RBAC identity in `app/main.py`). When you hit one, check whether its stated upgrade condition is now true before treating it as tech debt to silently "fix."
- `docs/MIGRATION_TRACKER.md`'s status table and Decisions Log are kept up to date as work lands — check it before assuming a feature (e.g. real OSRM routing, OR-Tools VRP, Kafka, RBAC) is implemented; several agents intentionally use simpler heuristics than the original TDD design until the tracker says otherwise.
- Every new agent must satisfy `Recommendation.validate_explainable()` — non-empty `evidence` and `rationale` — this is treated as a hard platform invariant, not a style preference.
