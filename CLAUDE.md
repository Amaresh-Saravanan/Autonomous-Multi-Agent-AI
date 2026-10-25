# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Autonomous multi-agent disaster-response platform. Device-authenticated sensor events flow through ingestion normalizers → a queued, conditionally-skipped chain of 8 AI agents on LangGraph (rule-based with optional LLM reasoning) → recommendations with mandatory evidence/rationale, persisted and RBAC/agency-scoped → a live map dashboard, over HTTP + WebSocket. Agents only ever recommend; a human operator approves, rejects, or overrides every recommendation.

Design docs: `docs/PRD.md` (requirements/goals), `docs/TDD.md` (architecture/stack), `docs/ARCHITECTURE.md`, `docs/UX_DESIGN.md` (dashboard design), `docs/RUNBOOK.md` (day-to-day operation). `docs/archive/` holds superseded migration-era docs (the backend-v2 migration write-ups, old phase trackers) — useful for history, not current status.

## Commands

Run from `backend-v2/`:

```bash
python -m pip install -r requirements.txt
alembic upgrade head                          # apply DB migrations
python -m uvicorn app.main:app --reload --port 8001   # start API
python -m pytest tests/ -v                    # all tests
python -m pytest tests/test_some_file.py -v   # single test file
```

Or `docker compose up -d` from `backend-v2/` to bring up Postgres, Redis, and the API together (the API container runs migrations and starts itself).

Frontend is a Next.js + TypeScript + Tailwind app in `frontend-next/` (`npm install && npm run dev`, serves on `localhost:3000`, connects to `localhost:8001`).

LLM reasoning is optional — set `GROQ_API_KEY` to enable it via `app/infrastructure/llm.py`'s `LLMService`; every agent falls back to rule-based/threshold logic without it. Redis, unlike v1, is **mandatory** here — the blackboard has no silent in-memory fallback (see `app/orchestration/state.py`).

## Architecture

**Request flow:** `POST /api/v1/ingestion/{source_type}` (`app/api/ingestion.py`, device-authenticated via `app/security/devices.py`) → `IngestionService` (`app/ingestion/service.py`) normalizes the payload into an `Event` and enqueues it, returning `202` immediately — the agent chain runs out-of-request. A background worker thread (`start_worker_thread` in `app/orchestration/graph.py`) dequeues the job and calls `run_for_event()`, which builds a LangGraph `StateGraph` over the fixed `AGENT_CHAIN` (`app/orchestration/router.py`), runs it, detects conflicts (`app/recommendations/conflict.py`), updates the incident's severity from AG-1's result, and pushes the result over Redis pub/sub to connected `/ws/alerts` WebSocket clients (`app/infrastructure/websocket.py`).

**Agent contract** (`app/agents/base.py`): every agent is a `BaseAgent` subclass implementing `execute(context) -> AgentResult`. `run()` is the template method the orchestrator actually calls: it invokes `execute()`, then `validate_result()` — which raises `AgentExecutionError` if `evidence` or `reasoning` is empty, the one enforcement point for the platform's "every recommendation is explainable" invariant. If `execute()` raises for any reason, `run()` catches it and returns a `fallback()` result (status `FAILED`/`DEGRADED`) instead of crashing the pipeline — one agent's failure must never take down the others or the rest of the chain. Don't add an agent output path that bypasses `validate_result()`.

**Orchestration** (`app/orchestration/`): `router.py` defines the fixed data-dependency order — `AGENT_CHAIN` = AG-1 Disaster → AG-2 Damage → AG-3 Rescue → AG-4 Medical → AG-5 Allocation → AG-6 Route → AG-8 Situational (AG-1 first because it defines the incident, AG-8 last because it summarizes the whole blackboard). Unlike v1, agents are **not** all unconditionally run: `conditions.should_run()` skips dispatch agents (AG-3..AG-6) when the incident's severity is below `MIN_DISPATCH_SEVERITY` (0.3) — real trigger-based scheduling, not v1's "every agent runs on every event." AG-7 (citizen chat) is intentionally excluded from the chain; it's invoked directly from `app/api/citizen.py` since it's request/response, not event-triggered.

**Blackboard** (`app/orchestration/state.py`): `BlackboardService` is Redis-backed shared state keyed by incident, one hash field per agent, with optimistic concurrency (WATCH/MULTI) so two workers racing on the same incident never silently lose a write. No in-memory fallback — code should assume Redis is present and reachable.

**Agents** live in `backend-v2/app/agents/`, one subpackage per agent (`disaster_assessment/`, `damage_assessment/`, `rescue_planning/`, `medical_coordination/`, `resource_allocation/`, `route_optimization/`, `situational_intelligence/`, `citizen_assistance/`).

**LLM usage** (`app/infrastructure/llm.py`): `LLMService`, config-driven model name (`LLM_MODEL`, no hardcoded model), lazy-initialized on first call. Every call returns a typed `LLMResult` with an explicit `status` (`SUCCESS`/`DEGRADED`) and `reasoning_mode` (`llm`/`deterministic_fallback`) — a caller that ignores `status` gets `content=None`, not a plausible-looking fallback string, so treating a failure as a success is a visible bug. Don't make any agent hard-depend on the LLM being available.

**Human-in-the-loop & RBAC**: `app/recommendations/service.py`'s `decide()` applies approve/reject/override — only a still-`PENDING` recommendation can be decided; a second decision on an already-decided recommendation is rejected outright (v2's equivalent of "stale approvals must not resurrect an older state"). Role/permission checks live in `app/security/permissions.py` (`VIEWER < OPERATOR < ADMIN`, `require_role`/`require_permission`/`require_agency_access`) and are enforced in the backend service layer — never in the frontend. Situation-level agents (AG-1, AG-2, AG-8 — `GLOBAL_AGENTS` in `app/recommendations/service.py`) are visible to any authenticated user; resource-targeted agents (AG-3..AG-6) are scoped to the owning agency plus ADMIN. A recommendation whose agency can't be resolved stays ADMIN-only — never implicitly global.

**Severity grid**: `app/geo.py` does lat/lon rounding (geohash-lite quantization) for grid cells — deliberately not the `h3-py` library (ported decision from v1, see `docs/archive/BACKEND_V2_MIGRATION_ANALYSIS.md`).

## Git workflow

- Run the backend-v2 test suite (`python -m pytest tests/ -v` from `backend-v2/`) after any change before considering it done.
- Always ask for confirmation before pushing to `main` (or any branch). There is no standing push authorization — confirm first, every time.
- Never force-push or rewrite history without explicit request.

## Conventions specific to this repo

- `ponytail:` comments mark a deliberate simplification with a known ceiling and an explicit upgrade trigger (e.g. the lat/lon grid quantization instead of `h3-py` in `app/geo.py`, straight-line routing instead of real OSRM). When you hit one, check whether its stated upgrade condition is now true before treating it as tech debt to silently "fix."
- `docs/archive/` holds historical migration/phase-tracker docs — useful for *why* a decision was made, not for *current* status; check the current code (and these docs' dates) before assuming something described there still applies.
- Every agent must satisfy `BaseAgent.validate_result()` — non-empty `evidence` and `reasoning` — this is treated as a hard platform invariant, not a style preference.
- `backend/` is the legacy v1 backend, kept as a reference only. It is not deployed and should not be modified for new feature work.
