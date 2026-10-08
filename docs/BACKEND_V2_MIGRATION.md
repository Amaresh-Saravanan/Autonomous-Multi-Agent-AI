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
| 1 | Configuration | DONE | PASS (4 tests) | `app/config.py`: dev fallback secret, prod fail-safe, CORS parsing |
| 2 | DB models + Alembic | MODELS DONE, ALEMBIC NEXT | PASS (SQLite, 2 tests) / NOT VERIFIED — PostgreSQL unavailable | All 20 tables in `app/models/*`; portable lat/lon (no mapped PostGIS column — `geom` added by migration, Postgres-dialect only, per analysis §16.6) |
| 3 | Redis | NOT STARTED | - | `app/infrastructure/redis.py` next |
| 4 | API error system | DONE | not yet exercised via HTTP (handlers not wired into `main.py` yet) | `app/errors.py`: AppError hierarchy + 2 FastAPI exception handlers |
| 3 | Redis | DONE | PASS (fakeredis, 4 tests) | `app/infrastructure/redis.py`: real client factory, no silent in-memory fallback (fixes V1 problem #2) |
| 6 | Auth | DONE | PASS (6 tests) | `app/security/{jwt,auth,permissions}.py`: persistent users, argon2, JWT, `require_user`/`require_role`/`require_permission`/`require_agency_access`; `POST /api/v1/auth/login` wired |
| 7 | Device auth | DONE | PASS (4 tests) | `app/security/devices.py`: `require_device(source_type)`; wrong secret / wrong source_type / revoked all rejected |
| 11 | Blackboard | DONE | PASS (4 tests incl. 2-client race) | `app/orchestration/state.py`: Redis hash + WATCH/MULTI compare-and-update, `ConcurrencyError` on exhausted retries |
| 8-10,12-31 | — | NOT STARTED | - | See phase list in original spec message |

**Resume point:** next action is Phase 8-10: `app/ingestion/` (schemas,
validators, normalizers for iot/weather/satellite/citizen) +
`app/incidents/service.py` (persisted incidents + clustering) +
`app/infrastructure/queue.py` (memory/redis-backed), landing ingestion as
`202 Accepted` + background processing per Phase 8's mandate. Alembic
migration (rest of Phase 2) is still pending — tracked here so it isn't
dropped; SQLite `create_all()` is covering tests in the meantime.
`app/main.py` has `register_exception_handlers` + the auth router wired;
further routers get added as their underlying services land.

## Component migration table (populated incrementally)

| V1 location | V2 destination | Classification | Status | Reason | Tests |
|---|---|---|---|---|---|
| `app/models.py` (dataclasses) | `app/models/*.py` (SQLAlchemy ORM) | REWRITTEN | DONE | In-memory dataclasses → persisted tables (Phase 2 requirement) | `tests/unit/test_models.py` |
| `app/config` (scattered env reads / none) | `app/config.py` | REWRITTEN | DONE | Centralized `pydantic_settings`, fail-safe JWT secret | `tests/unit/test_config.py` |
| (none in V1 — errors were bare exceptions/500s) | `app/errors.py` | BUILD | DONE (not yet wired into app) | Phase 4 structured error contract | none yet (no HTTP surface) |

## Environment facts (do not re-verify without new evidence)

- Docker daemon unavailable → PostgreSQL/PostGIS and real Redis are
  **NOT VERIFIED** throughout. SQLite + `fakeredis` back all automated tests.
- `ortools` not installed → AG-5 optimizer strategy is **DEFERRED**.
- Drone / social / GIS ingestion have no V1 implementation → **not exposed**
  in V2 per the spec's own rule.
- V1 (`backend/`) stays untouched as the reference implementation; 74 V1
  tests are the behavioral baseline and are not modified.
