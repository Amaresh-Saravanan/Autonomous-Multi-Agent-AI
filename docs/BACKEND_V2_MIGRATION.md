# Backend V2 Migration Tracker

Branch: `backend-v2-migration`. Source analysis: `docs/BACKEND_V2_MIGRATION_ANALYSIS.md`
(Phase 0 — read first, not re-derived here). This file is the resumable
source of truth for migration progress: if a session restarts, read the
phase table below to see what's done, what's next, and what's blocked.

Validation legend: **PASS** (test executed and green) · **NOT VERIFIED —
external service unavailable** (PostgreSQL/PostGIS/Redis/Docker/OSRM/Groq not
reachable in this environment; code + SQLite/fakeredis-backed tests exist) ·
**DEFERRED** (interface exists, implementation intentionally not built).

## Phase status

| Phase | Area | Status | Validation | Notes |
|---|---|---|---|---|
| 0 | Analysis | DONE | PASS | `docs/BACKEND_V2_MIGRATION_ANALYSIS.md` |
| 1 | Configuration | IN PROGRESS | - | |

(Table filled in as each phase lands — see component table below for the
authoritative per-component record once populated.)

## Component migration table (populated incrementally)

| V1 location | V2 destination | Classification | Status | Reason | Tests |
|---|---|---|---|---|---|

## Environment facts (do not re-verify without new evidence)

- Docker daemon unavailable → PostgreSQL/PostGIS and real Redis are
  **NOT VERIFIED** throughout. SQLite + `fakeredis` back all automated tests.
- `ortools` not installed → AG-5 optimizer strategy is **DEFERRED**.
- Drone / social / GIS ingestion have no V1 implementation → **not exposed**
  in V2 per the spec's own rule.
- V1 (`backend/`) stays untouched as the reference implementation; 74 V1
  tests are the behavioral baseline and are not modified.
