# Backend V2 Migration — Final Report

Branch: `backend-v2-migration`. Scope: `backend/` (V1, untouched) →
`backend-v2/` (new). All 32 phases of the migration spec were executed;
this report is the final rollup. Per-phase detail lives in
`docs/BACKEND_V2_MIGRATION.md`; the architecture/API/DB/agent docs are
listed under Documentation below.

## V1 baseline

- 74 tests, all passing, `backend/` ~1,700 lines.
- 20 problems identified by direct code reading (not assumption) in
  `docs/BACKEND_V2_MIGRATION_ANALYSIS.md` §10 — in-memory state, hidden
  network calls on the hot path, LLM failures silently reported as
  successful rationales, hardcoded Chennai fallback coordinates, open
  ingestion/citizen-chat/WebSocket, no agency enforcement, no override
  decision, straight-line "routing," population-heuristic "damage
  assessment," keyword-overlap "RAG."
- **V1 is untouched.** Still 74/74 passing; verified again at the end of
  this migration, not just at the start.

## What V2 is

A parallel `backend-v2/` FastAPI application: SQLAlchemy 2.0 (sync) +
PostgreSQL/PostGIS in production, Redis for the blackboard/queue/pub-sub,
LangGraph for orchestration, JWT + device-credential auth, and a typed
contract (Pydantic) on every request/response and every agent
input/output. 70 tests, all passing, run against SQLite + `fakeredis`.

## Components migrated / refactored / rewritten / discarded

Full table in `docs/BACKEND_V2_MIGRATION.md`. Summary counts:

- **MIGRATED** (logic preserved, ported to typed V2 shapes): normalizers,
  geo helpers, incident clustering rule, all 8 agents' core reasoning,
  conflict-check concept, role hierarchy.
- **REFACTORED** (same idea, new structure): resource allocation (now
  behind a `Strategy` interface), route calculation (now behind a
  `RoutingService` interface), orchestration (router/conditions/execution
  split out of one file).
- **REWRITTEN** (new implementation, same job): `llm.py`, auth, WebSocket,
  ingestion endpoints, AG-7 retrieval, blackboard, recommendations, audit,
  alerts, `validate_explainable` (now a typed `AgentExecutionError`
  path, not a strippable `assert`).
- **DISCARDED**: hardcoded users/secret, `mixtral-8x7b-32768`, the
  module-global WebSocket client list, the `[80.27, 13.08]` Chennai
  fallback, the synchronous in-request agent pipeline, the hidden
  Nominatim geocode call.

## New architecture

See `docs/BACKEND_V2_ARCHITECTURE.md` for the full request-flow diagram
and layering. Headline structural changes:

- **Durable state everywhere it matters.** 20 Postgres tables (Alembic
  migration verified against SQLite; PostGIS path NOT VERIFIED — no
  Postgres available). Redis blackboard with optimistic-concurrency
  `merge()` — proven under a genuine 2-client race in
  `tests/unit/test_blackboard.py`.
- **Ingestion is async.** Device-authenticated → validate → normalize →
  persist → associate incident → enqueue → **202**. A background worker
  thread drains the queue and runs the LangGraph chain out-of-request.
- **Every agent failure is isolated and typed.** `BaseAgent.run()` never
  lets an exception escape; LLM failures return a typed `DEGRADED` result
  with a `fallback_reason`, never a string an agent could mistake for a
  successful rationale.
- **Agency isolation is enforced in the backend, in every query** —
  `require_agency_access`, `Recommendation.target_agency_id` filtering,
  WebSocket broadcast filtering. A `NULL` target is never visible to
  everyone (the specific V1 bug named in the spec).
- **Human decision loop has all three outcomes**: approve, reject,
  override (ADMIN-only, requires a replacement action + reason), each
  audited.

## New database schema

`docs/BACKEND_V2_DATABASE.md`. 20 tables, UUID PKs, timezone-aware
timestamps, `Enum(..., native_enum=False)` columns (a real bug — plain
`String` columns don't coerce back to Python enums on read — found and
fixed mid-migration). PostGIS `geom` columns + sync triggers added by the
Alembic migration on the `postgresql` dialect only.

## API changes

`docs/BACKEND_V2_API.md`. All V2 routes versioned under `/api/v1` (except
`/health`, `/ws/alerts`). `POST /api/v1/recommendations/{id}/decide`
replaces V1's separate `/approve`/`/reject` endpoints and adds `override`.
Every ingestion endpoint (and citizen chat) requires device credentials
instead of being open.

## Frontend changes

`docs/BACKEND_V2_FRONTEND_COMPATIBILITY.md` — full endpoint-by-endpoint
diff. Applied: login path+field, `/api/v1` path prefixes, unified decide
endpoint, async-202 ingestion flow (`onIngested` no longer expects
recommendations synchronously), authenticated WebSocket
(`?token=<JWT>`), and the WS message handler re-fetching recommendations
on alert receipt instead of reading them out of the socket payload (V2's
alert payload doesn't carry them). TypeScript typecheck is clean.
Deferred: metrics panel (format changed, not just path — Prometheus text
vs V1's JSON), citizen-reports list, severity-grid overlay (no V2
endpoint for either yet), citizen-chat device-auth wiring. No UI was
redesigned; no browser was driven against a live pair of servers (see
Docker/Redis status below).

## Tests run

| Suite | Count | Result |
|---|---|---|
| `backend/tests/` (V1, unmodified) | 74 | **PASS** |
| `backend-v2/tests/unit/` | 57 | **PASS** |
| `backend-v2/tests/integration/` | 9 | **PASS** |
| `backend-v2/tests/e2e/` | 1 (`test_flood_scenario.py`) | **PASS** |
| `backend-v2/tests/` (root, health) | 3 | **PASS** |
| `backend-v2` total | 70 | **PASS** |
| `frontend-next` TypeScript (`tsc --noEmit`) | — | **PASS** (clean) |

Coverage includes every item Phase 26 named as a minimum: auth, RBAC,
agency isolation, device auth, input validation, normalization, incident
creation/clustering, blackboard concurrency, LLM success/failure/fallback,
AG-1..AG-8, recommendation create/approve/reject/override, conflict
detection, audit, alert filtering, WebSocket auth + agency filtering,
agent failure recovery (the FAILED/DEGRADED paths in
`tests/unit/test_agents.py` and `test_llm.py`).

## Docker / external services

`backend-v2/Dockerfile` + `docker-compose.yml` exist (backend + PostGIS
Postgres + Redis, with health-checked startup ordering and an
`alembic upgrade head` on boot). **NOT VERIFIED** — no Docker daemon is
reachable in this environment (`docker ps` fails). Real PostgreSQL, real
Redis, real OSRM, and a live Groq call are likewise **NOT VERIFIED** —
every path that touches them is exercised against SQLite/`fakeredis`/a
fake LLM client instead, and the code never silently substitutes one of
those for the real thing in a production code path (the opposite of V1's
problem #2).

## Deferred features (interface exists, not implemented)

OR-Tools VRP optimization, real satellite/CV damage detection, real
OSRM/Valhalla routing, vector-store RAG, drone/social/GIS ingestion,
predictive impact modeling, Kafka, Kubernetes scaling,
`event_sources`/`recommendation_evidence`/`resource_allocations`/
`routes`/`route_status` row population, a citizen-reports list endpoint,
an incident severity-grid endpoint, and a V2 JSON metrics endpoint. Full
table with the interface location for each: `docs/BACKEND_V2_MIGRATION.md`
§"Deferred features."

## Known limitations

- Real PostgreSQL/PostGIS and real Redis are unverified in this sandbox;
  the production code paths exist and are written against the real
  client libraries, but nothing here has proven they work against the
  real services.
- `backend-v2` cannot fully boot (`uvicorn app.main:app`) without a
  reachable Redis — intentional (Phase 3/11/21/22 forbid a silent
  in-memory fallback), but it means a live end-to-end browser
  verification wasn't possible here.
- Several DB tables exist with no writer yet (see Deferred list) —
  schema-ready, not wired.
- The frontend's citizen-chat widget doesn't yet send device credentials,
  so it will 401 against V2 until that's wired.

## Recommended next implementation steps

1. Stand up Postgres + Redis (locally or via the provided
   `docker-compose.yml`) and re-run the validation matrix in
   `docs/BACKEND_V2_MIGRATION_ANALYSIS.md` §19 for real, converting every
   NOT VERIFIED line to PASS or a filed bug.
2. Wire a demo device credential into the citizen-chat widget, or build a
   lighter-weight end-user auth path if device credentials turn out to be
   the wrong model for a public chat widget.
3. Build the citizen-reports list and severity-grid endpoints (both have
   persisted data already; only the read APIs are missing).
4. Decide whether `event_sources`/`recommendation_evidence`/
   `resource_allocations`/`routes` need real writers or should be dropped
   from the schema if they stay unused.
5. When OR-Tools/OSRM/a vector store are actually prioritized, implement
   them behind the existing `AllocationStrategy`/`RouteProvider`/
   `VectorStore` interfaces — no call site should need to change.
