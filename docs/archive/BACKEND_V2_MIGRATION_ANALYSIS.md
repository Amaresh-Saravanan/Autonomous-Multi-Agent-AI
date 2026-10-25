# Backend V2 Migration Analysis

Date: 2026-10-08 · Branch: `backend-v2-migration` · Scope: `backend/` (V1) → `backend-v2/`

This is Phase 0 output. It records what V1 actually does (read from source, not
from the tracker), what V2 takes from it, and what V2 deliberately does not.
V1 stays untouched. Claims about V1 come from reading the code; claims about what
is installed or runnable on this machine come from commands run on 2026-10-08.

## 0. Environment facts that constrain validation

| Fact | Evidence | Consequence |
|---|---|---|
| V1 test suite: 74 passed | `python -m pytest tests -q` in `backend/` | Behavioral baseline for parity checks |
| Docker daemon not running | `docker ps` → cannot connect to `dockerDesktopLinuxEngine` | No PostgreSQL/PostGIS or Redis locally. Gates 2 and 3 cannot be verified against real services here |
| Installed: SQLAlchemy 2.0, Alembic, psycopg 3, pydantic-settings, langgraph, groq, PyJWT, argon2, bcrypt, tenacity, prometheus_client | `pip list` | Core stack available |
| Not installed: `redis`, `geoalchemy2`, `fakeredis`, `ortools` | `pip list` | First three are added to V2 requirements; OR-Tools stays deferred |
| Python 3.11.9 | `python --version` | Target version |

Validation therefore uses SQLite (same SQLAlchemy models; PostGIS columns are a
Postgres-only variant) and `fakeredis` for automated tests. The PostgreSQL/PostGIS and
real-Redis paths are written against the same interfaces and marked **requires
external configuration; not verified here** until run against `docker compose up`.

## 1. Existing architecture

FastAPI app (`app/main.py`, 220 lines) holding every route, a CORS block, a metrics
middleware and a module-global WebSocket client list. Domain state lives in module
globals: `blackboard._mem`, `recommendations._recs`, `audit._log`,
`incidents._incidents`, `severity_grid._grid`, `citizen_reports._reports`,
`alerts._last_pushed`, `metrics._routes`, `auth.USERS`, `resources.*` (synthetic
lists). Agents are classes in `backend/agents/` that import `app.resources` directly.
`app/orchestrator.py` builds a LangGraph `StateGraph` as a fixed linear chain and
runs it synchronously inside the ingest request.

## 2. Existing data flow

`POST /ingest/{source_type}` (open, `raw: dict`) → `normalizers.normalize` → `Event`
→ `incident_id = raw.incident_id or incidents.assign_incident(event)` (geocode via
Nominatim, else 5 km / 1 h clustering) → blackboard enrichment with state/district →
`orchestrator.run` (agents in order; each: read blackboard, `agent.run`, merge, audit,
record recommendation; AG-1 also updates the severity grid) → conflict check (AG-5 vs
AG-6 only) → `alerts.should_push` → broadcast to every WebSocket client → HTTP
response contains all recommendations.

## 3. Existing API routes (V1)

| Method + path | Auth | Notes |
|---|---|---|
| GET `/health` | open | `{status, using_redis}` |
| POST `/auth/login` | open | `body: dict`; returns `{access_token, token_type}` |
| GET `/metrics` | operator+ | per-route count/avg/p95 + acceptance rate |
| GET `/resources` | viewer+ | hospitals, shelters, teams, ambulances, supplies |
| GET `/incidents` | viewer+ | registry list, newest first |
| GET `/incidents/{id}` | viewer+ | raw blackboard dict |
| GET `/incidents/{id}/severity` | viewer+ | GeoJSON FeatureCollection |
| GET `/audit` | admin | all entries |
| POST `/ingest/{source_type}` | **open** | runs the full agent chain synchronously |
| GET `/recommendations?status=` | viewer+ | filtered by `target_agency` (no-op today) |
| POST `/recommendations/{id}/approve`, `/reject` | operator+ | audited |
| POST `/citizen/chat` | **open** | AG-7 |
| GET `/citizen/reports?incident_id=` | viewer+ | |
| WS `/ws/alerts` | **open** | broadcast to every client |

## 4. Existing agents

All return one `Recommendation` and call `validate_explainable()` (assert-based;
asserts vanish under `python -O`).

| Agent | Triggers | Logic (as read) |
|---|---|---|
| AG-1 | iot, weather, satellite | LLM path: prompt → `json.loads(response)`; on parse error severity 0.5. Fallback: `THRESHOLDS = {water_level: (3.0, 5.0)}` linear 0.5→1.0. Only `water_level` has a rule |
| AG-2 | iot, satellite | `severity × 4500/km² × π·2² × 0.3`; structures `severity × 40`; confidence 0.55. Constants, not data |
| AG-3 | iot | nearest `available` team from `TEAMS`; priority critical ≥0.85 / high ≥0.5 |
| AG-4 | iot | casualties = 2% of affected; hospital with free beds; nearest ambulance |
| AG-5 | iot | nearest shelter with free capacity; supplies needed vs stock |
| AG-6 | iot | straight line to nearest shelter (ignores capacity); radius check against one hardcoded blocked segment |
| AG-7 | on demand | keyword-overlap retrieval over 7 synthetic docs; LLM or canned reply |
| AG-8 | all | joins other agents' actions; LLM summary optional |

## 5. Existing storage

Everything is process memory. Only the blackboard can use Redis (`REDIS_URL`),
as read-modify-write with no locking or versioning (`merge` = `get` then `set`; two
workers lose updates). No database is used anywhere. `docker-compose.yml` provisions
PostGIS + Redis that nothing consumes.

## 6. Existing authentication

PyJWT HS256, 4 h expiry, roles admin/operator/viewer with a rank hierarchy, PBKDF2
(100k) password hashing, four hardcoded users, `JWT_SECRET` falls back to a literal
dev string with a warning. `agency` is in the token but enforced nowhere (the filter
is a no-op). Ingest, citizen chat and the WebSocket are unauthenticated.

## 7. Existing orchestration

LangGraph `StateGraph`, fixed edge chain AG-1→2→3→4→5→6→8. Trigger routing is a
per-node `source_type in agent.triggers` skip. No router node, no failure isolation
(an agent exception aborts the whole request), no per-agent timing or health.
Conflict detection is one hardcoded AG-5/AG-6 shelter comparison.

## 8. Frontend ↔ backend integration (`frontend-next/lib/api.ts`, `operations-context.tsx`)

Calls: `/auth/login`, `/resources`, `/recommendations`, `/incidents`, `/audit`,
`/metrics`, `/citizen/chat`, `/incidents/{id}`, `/citizen/reports`,
`/incidents/{id}/severity`, `/recommendations/{id}/approve|reject`, `/ingest/iot`
(demo ingest form), and `WS /ws/alerts` with **no token**. The WS payload is
`{incident_id, recommendations[]}`. The frontend reads `Recommendation` fields
`rec_id, incident_id, agent_id, action, rationale, confidence, severity, status
(pending|approved|rejected), created_at, evidence[], geo, details, target_agency`.
`ingestWaterLevel` consumes recommendations from the *ingest response*, which cannot
survive an asynchronous 202 pipeline (see the compatibility matrix in
`BACKEND_V2_MIGRATION.md`).

## 9. Existing tests

74 tests across 18 files: slice, agents, scenario (escalating flood replay), trigger
routing, conflicts, incidents/clustering, alerts, audit coverage, auth/RBAC,
recommendations, citizen RAG/reports/verification, blackboard chaos, metrics,
incident-list/audit routes. They exercise V1 module globals and `TestClient(app)`.
They are reusable as *behavioral specs* (inputs → expected agent outputs), not as
code, because they reset module globals.

## 10. Problems discovered

1. **State is volatile and per-process.** Audit, recommendations, incidents, severity
   grid, citizen reports, alert dedup and metrics vanish on restart and diverge
   across workers.
2. **Blackboard `merge` is not atomic.** Read-modify-write. The Redis connection is
   probed once at import, so a transient outage at boot silently switches the process
   to in-memory for its lifetime.
3. **Ingest runs the whole pipeline in the request.** Latency is the sum of all agents
   plus a Nominatim call (5 s timeout) in-request.
4. **No failure isolation.** One agent exception fails ingestion with a 500.
5. **`geocode.reverse` is a hidden network call** on the hot path, with a module-level
   `httpx.Client` created at import.
6. **`validate_explainable` uses `assert`.** Stripped under `-O`; raises
   `AssertionError`, not a typed error.
7. **LLM:** hardcoded `mixtral-8x7b-32768`; a connectivity probe runs at import; failures
   are returned as strings (`"[LLM call failed: …]"`) that agents then store as the
   rationale, so an LLM failure is presented as a successful result. AG-1 also reports
   confidence 0.85 whenever the LLM is merely *available*, even when its output failed
   to parse.
8. **AG-1 LLM parse-failure path** reads `response` in its `except` block; it is bound
   today only because `reason()` swallows every exception.
9. **Agents import the resource registry directly** and fall back to hardcoded
   coordinates `[80.27, 13.08]` (Chennai) when AG-1 has no geo. That silently
   fabricates a location.
10. **AG-6 ignores AG-5's capacity decision** by design; the conflict detector exists
    to flag that disagreement rather than routing to AG-5's chosen shelter.
11. **Auth:** seeded users with known passwords, insecure default secret, `agency`
    never enforced, no refresh or logout.
12. **Open write endpoints** (ingest, citizen chat) and an open WebSocket broadcasting
    every incident to anyone.
13. **`_decide` race:** read rec, mutate, write, check blackboard, with no transaction.
14. **No `override` decision**, no `expires_at`, no `OVERRIDDEN`/`EXPIRED` states.
15. **Metrics** are a per-process deque with a naive percentile.
16. **Raw `dict` bodies** on login, ingest and citizen chat.

## 11. Components to MIGRATE (logic preserved, adapted to V2 types)

| V1 | V2 destination |
|---|---|
| `normalize_iot/weather/satellite/citizen` field mapping | `ingestion/normalizers/*.py`, driven by typed request schemas |
| `geo_utils.distance_km`, `cell_id`, `cell_polygon` | `app/geo.py` (one small module) |
| `severity_grid.update` max-per-cell rule + GeoJSON | incident severity grid service (persisted) |
| AG-1 threshold curve | `agents/disaster_assessment/rules.py` |
| AG-2 constants + formulas | `agents/damage_assessment/` as a labelled prototype estimator |
| AG-3 priority bands, nearest-team rule | `agents/rescue_planning/` |
| AG-4 casualty heuristic, hospital selection key | `agents/medical_coordination/` |
| AG-5 greedy shelter pick + supply shortfall | `agents/resource_allocation/` as the `GreedyFallback` strategy |
| AG-6 straight-line + blocked-radius test | `services/route_service.py` as a labelled `StraightLineFallback` provider |
| AG-8 aggregation | `agents/situational_intelligence/` consuming typed `AgentResult`s |
| `citizen_verification.score_confidence` thresholds | citizen normalizer / verification helper |
| Clustering rule (district + 1 h, else 5 km + 1 h) | `incidents/clustering.py`, pure function over persisted candidates |
| `alerts.should_push` threshold 0.5 + dedup on (action, severity) | `services/alert_service.py` with a persisted dedup key |
| Recommendation fields incl. `details`, `target_agency` | schemas + ORM |
| AC-4 conflict concept | `recommendations/conflict.py`, generic `ConflictDetector` |
| Role hierarchy viewer<operator<admin; PBKDF2 → argon2 | `security/` |
| V1 tests as behavior specs | `tests/unit/*`, rewritten against V2 interfaces |

## 12. Components to REFACTOR (same idea, new structure)

`main.py` (split into routers), `orchestrator.py` (router + conditions + isolated
execution), `blackboard.py` (service with versioning), `recommendations.py`,
`audit.py`, `metrics.py` (prometheus_client), the resource registry (tables), the
incident service (persisted + lifecycle), the human decision flow (approve / reject /
override in one transaction).

## 13. Components to REWRITE

`llm.py` (provider abstraction, config-driven model, result metadata, no import-time
probe), auth (DB users, agencies, permissions), WebSocket (authenticated, filtered,
Redis pub/sub), ingestion endpoints (typed, device-authenticated, 202), AG-7 retrieval
(Retriever / VectorStore interface), `validate_explainable` (typed error, not
`assert`).

## 14. Components to DISCARD

Hardcoded users and the insecure `JWT_SECRET` default; `mixtral-8x7b-32768`;
module-global `_ws_clients`; hardcoded Chennai fallback coordinates; the synchronous
in-request pipeline; `geocode.py` as an implicit hot-path call (geocoding becomes an
optional, injected enrichment with a timeout); synthetic resource lists as runtime data
(kept only as a clearly marked dev seed script); the naive keyword RAG as the final
design (its 7-document corpus survives as a documented development fallback corpus).

## 15. Missing capabilities required by the PRD

| PRD | V2 plan |
|---|---|
| SEC-1 agency-scoped RBAC | **Build**, enforced in queries |
| SEC-2 / NFR auditability (durable, immutable) | **Build**: Postgres append-only audit |
| AC-5 override | **Build**: `OVERRIDDEN` + replacement action + reason |
| AC-4 general conflicts | **Build**: pluggable `ConflictDetector` |
| AC-2 trigger scheduling | **Build**: router + conditions |
| NFR resilience (agent failure ≠ crash) | **Build**: per-agent isolation + health |
| DI-1/4 satellite/weather ingestion | **Build** typed schemas + normalizers (they exist in V1) |
| DI-2 drone, DI-5 social, DI-6 GIS ingestion | **Defer.** No V1 logic exists; per the spec's own rule ("only expose endpoints that are actually implemented"), no endpoint is exposed until a real normalizer exists |
| DS-2 predictive impact | **Defer** (needs a weather + trend model) |
| AG-6 real road routing (OSRM/Valhalla) | **Interface now, provider deferred**: needs an OSRM service |
| AG-5 OR-Tools | **Interface now, optimizer deferred**: `ortools` not installed; strategy slot exists |
| AG-2 imagery damage detection | **Defer**; estimator is labelled prototype/degraded |
| AG-7 vector RAG | **Interface now**; development fallback = keyword retriever, documented |
| NFR 10k sensors / 100 operators | **Not claimed.** Queue-based ingestion removes the known V1 bottleneck, but no load test is run in this migration |
| DS-6 external push (SMS/email) | **Defer** |
| 99.9% availability, TLS in transit / at rest | Deployment concern; not claimed |

## 16. Proposed Backend V2 architecture

```
Device/API client ─▶ api/ingestion (device auth, pydantic, 202)
        ─▶ ingestion.service (normalize ▶ persist Event ▶ associate Incident)
        ─▶ Queue (memory | redis) ─▶ worker
        ─▶ orchestration (router ▶ conditional agents ▶ aggregate ▶ conflicts ▶ recommendations)
        ─▶ Postgres (durable) + Blackboard (Redis hot state) ─▶ AlertService ─▶ Redis pub/sub
        ─▶ WebSocket (JWT, agency + incident filtered) ─▶ frontend-next
Human: api/recommendations approve | reject | override ─▶ one transaction ─▶ audit
```

**Deviations from the suggested tree, and why:**

1. **Sync SQLAlchemy 2.0 + psycopg 3, not async.** Agents are light, V1 tests are sync,
   `fakeredis`/SQLite validation is simpler, and FastAPI runs `def` endpoints in a
   threadpool. The WebSocket and the queue worker are the async edges.
2. **`models/` is the ORM package and `schemas/` the Pydantic package**, as suggested;
   per-agent `schemas.py` hold agent-specific typed input/output.
3. **`prompts.py` / `rules.py` exist only where there is content** (AG-1). No empty
   placeholder files.
4. **No `drone`, `social`, `gis` normalizers or endpoints** (see section 15).
5. **A single `app/geo.py`** instead of scattered geo helpers.
6. **PostGIS columns are a Postgres-only variant.** Portable `latitude`/`longitude`
   columns are the source of truth for logic; a `geom` column is added on PostgreSQL
   for spatial queries. SQLite (tests) omits it.

## 17. Migration order

1. Branch + analysis (this doc). 2. Structure, config, error types, logging.
3. Schemas. 4. DB models + Alembic. 5. Blackboard (memory + Redis, versioned).
6. Security (users/agencies/roles/devices, JWT, dependencies). 7. Ingestion +
normalizers + incident service/clustering. 8. Queue + worker. 9. LLM service.
10. Agent framework + AG-1..AG-8. 11. Orchestration. 12. Recommendations + conflicts +
human decision + audit. 13. Alerts + WebSocket. 14. Agent health + observability.
15. API compatibility + minimal frontend changes. 16. E2E test. 17. Docs + checklist.

## 18. Risks

| Risk | Mitigation |
|---|---|
| Postgres/PostGIS/Redis paths unverifiable here | Same interfaces exercised on SQLite/fakeredis; Postgres migration marked unverified; documented `docker compose` verification steps |
| Scope exceeds one session | Core first (spec Phase 35); advanced items listed as deferred with their interface in place |
| Behavior drift from V1 | Port V1 test inputs/expected outputs as parity tests per agent |
| Frontend breakage | Compat routes for read endpoints; ingest response + WS token are the only documented frontend changes |
| Async ingestion changes demo UX | Ingest form relies on WS/poll to show results (documented change) |
| LLM unavailable in tests | Deterministic path is the default and always tested; the LLM provider is tested with a fake client |

## 19. Validation strategy

Per-gate evidence is recorded in the final report with the command run and its output:
app start (`/health`), SQLite DB + Alembic `upgrade head`, fakeredis blackboard and
queue, auth/RBAC tests, ingestion validation tests, event + incident persistence,
agent unit tests with V1 parity inputs, recommendation + human-decision + audit tests,
WebSocket authorization tests via `TestClient.websocket_connect`, and one E2E test
through HTTP → queue → graph → approval → audit → WebSocket. Anything not executed
against real PostgreSQL, real Redis, Groq, OSRM, or a vector store is labelled
**not verified**.
