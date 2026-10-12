# Backend V2 Migration Tracker

Branch: `backend-v2-migration`. Source analysis:
`docs/BACKEND_V2_MIGRATION_ANALYSIS.md` (Phase 0 — read first, not
re-derived here). This file is the resumable source of truth: if a
session restarts, read the phase table below to see what's done, what's
next, and what's blocked.

Validation legend: **PASS** (test executed and green) · **NOT VERIFIED —
external service unavailable** (PostgreSQL/PostGIS/real Redis/Docker/OSRM
not reachable in this environment; code + SQLite/fakeredis-backed tests
exist and pass) · **DEFERRED** (interface exists, implementation
intentionally not built).

## Phase status

| Phase | Area | Status | Validation |
|---|---|---|---|
| 0 | Analysis | DONE | — |
| 1 | Configuration | DONE | PASS |
| 2 | DB models + Alembic | DONE | PASS (SQLite) / NOT VERIFIED — PostgreSQL |
| 3 | Redis | DONE | PASS (fakeredis) / NOT VERIFIED — real Redis |
| 4 | API error system | DONE | PASS |
| 5 | Pydantic API contracts | DONE | PASS (every endpoint has a typed request/response) |
| 6 | Authentication | DONE | PASS |
| 7 | Device authentication | DONE | PASS |
| 8 | Ingestion pipeline | DONE | PASS |
| 9 | Normalizers | DONE | PASS |
| 10 | Incident management | DONE | PASS |
| 11 | Blackboard | DONE | PASS (fakeredis, incl. 2-client race test) / NOT VERIFIED — real Redis |
| 12 | LLM service | DONE | PASS |
| 13 | Location handling | DONE | PASS (no fabricated coordinates anywhere; `location_unavailable_result()` in AG-3/4/5/6) |
| 14 | Base agent contract | DONE | PASS |
| 15 | Agent migration (AG-1..AG-8) | DONE | PASS |
| 16 | Orchestration (LangGraph) | DONE | PASS |
| 17 | Recommendation system | DONE | PASS |
| 18 | Human decision loop | DONE | PASS |
| 19 | Conflict detection | DONE | PASS |
| 20 | Audit | DONE | PASS |
| 21 | Alert engine | DONE | PASS |
| 22 | WebSocket security | DONE | PASS |
| 23 | Agent health | DONE | PASS |
| 24 | Observability | DONE | PASS |
| 25 | Frontend integration | DONE | PASS (typecheck) / browser not exercised — see note below |
| 26 | Test migration | DONE | PASS — 70 backend-v2 tests + 74 unmodified V1 tests, both green |
| 27 | E2E disaster scenario | DONE | PASS — `tests/e2e/test_flood_scenario.py` |
| 28 | Docker | DONE (config) | NOT VERIFIED — no Docker daemon in this environment |
| 29 | Migration tracker | DONE | this file |
| 30 | Documentation | DONE | `docs/BACKEND_V2_{ARCHITECTURE,API,DATABASE,AGENT_ARCHITECTURE,FRONTEND_COMPATIBILITY}.md` |
| 31 | Deferred features | DONE | see list below |

**Frontend note (Phase 25):** code changes are typechecked and reviewed;
no browser was driven against a live `backend-v2` + `frontend-next` pair
in this session, because `backend-v2` cannot fully boot without a real
Redis (Phase 3/11/21/22 all require one — no silent fallback, by design).
Mark live browser verification **NOT VERIFIED — Redis/Postgres
unavailable**, not PASS.

## Component migration table

| V1 location | V2 destination | Classification | Reason |
|---|---|---|---|
| `app/models.py` (dataclasses) | `app/models/*.py` (20 SQLAlchemy tables) | REWRITTEN | Persisted tables, not process memory (Phase 2) |
| scattered env reads / none | `app/config.py` | REWRITTEN | Centralized `pydantic_settings`, fail-safe JWT secret |
| bare exceptions → 500 | `app/errors.py` | BUILD | Structured `{error,message,details}` contract |
| `app/normalizers.py` | `app/ingestion/normalizers/{iot,weather,satellite,citizen}.py` | MIGRATED | Field mapping preserved; typed inputs, honest `location_state` |
| `app/geo_utils.py` | `app/geo.py` | MIGRATED | Same haversine + grid-cell math, one module |
| `app/incidents.py` | `app/incidents/service.py` + `clustering.py` | REFACTORED | Persisted; dropped the hidden Nominatim hot-path call (V1 problem #5) |
| `app/blackboard.py` | `app/orchestration/state.py` | REWRITTEN | Redis WATCH/MULTI compare-and-update; no silent lost updates (V1 problem #2) |
| `app/auth.py` (hardcoded users) | `app/security/{auth,jwt,permissions,devices}.py` | REWRITTEN | Persistent users, argon2, agency isolation, device credentials |
| `app/llm.py` | `app/infrastructure/llm.py` | REWRITTEN | Config-driven model, typed SUCCESS/DEGRADED result, no import-time probe |
| `agents/base.py` | `app/agents/base.py` | REWRITTEN | Typed `AgentResult`, `can_handle/execute/fallback/validate_result` |
| `agents/disaster.py` | `app/agents/disaster_assessment/*` | MIGRATED + IMPROVED | LLM failure/parse-failure never reported as success |
| `agents/damage.py` | `app/agents/damage_assessment/*` | MIGRATED + RELABELED | `DeterministicExposureEstimator`, explicit heuristic disclaimer |
| `agents/rescue.py` | `app/agents/rescue_planning/*` | MIGRATED | Injected resources, no hardcoded Chennai fallback |
| `agents/medical.py` | `app/agents/medical_coordination/*` | MIGRATED | Same pattern |
| `agents/allocation.py` | `app/agents/resource_allocation/*` | MIGRATED + REFACTORED | `GreedyFallback` behind an `AllocationStrategy` interface |
| `agents/route.py` | `app/agents/route_optimization/*` + `services/route_service.py` | MIGRATED + REFACTORED | `StraightLineFallback` behind a `RoutingService`/`RouteProvider` interface |
| `agents/citizen.py` (AG-7 chat fn) | `app/agents/citizen_assistance/*` | REWRITTEN | `Retriever`/`DocumentStore`/`VectorStore` interfaces; explicit "unavailable" path |
| `agents/situational.py` | `app/agents/situational_intelligence/*` | MIGRATED | Same aggregation logic over typed blackboard entries |
| `app/orchestrator.py` | `app/orchestration/{router,conditions,execution,graph}.py` | REWRITTEN | Conditional routing (severity-gated dispatch agents), per-agent isolation, persisted side effects |
| `app/recommendations.py` | `app/recommendations/service.py` | REWRITTEN | Persisted; `target_agency=NULL` no longer visible to everyone (V1 bug) |
| (one hardcoded check in `orchestrator.py`) | `app/recommendations/conflict.py` | REWRITTEN | Generic `ConflictDetector` over a `ConflictRule` list |
| `app/audit.py` | `app/services/audit_service.py` | REWRITTEN | Persisted, append-only (no update/delete method exists) |
| `app/alerts.py` | `app/services/alert_service.py` | REWRITTEN | Persisted dedup key; Redis pub/sub publish |
| (none — V1 has no health tracking) | `app/services/agent_health_service.py` | BUILD | Per-agent run history + rolling stats |
| V1 `/ws/alerts` (open, broadcast-all) | `app/infrastructure/websocket.py` + `api/websocket.py` | REWRITTEN | JWT auth, agency-filtered, Redis pub/sub bridge |
| `app/resources.py` (synthetic lists) | `app/services/resource_service.py` + `models/resource.py` | REWRITTEN | Persisted tables; synthetic numbers survive only as a labelled dev seed |
| hardcoded users + insecure default secret | — | DISCARDED | Replaced by persistent users (Phase 6) |
| `mixtral-8x7b-32768` | — | DISCARDED | Replaced by `LLM_MODEL` config |
| module-global `_ws_clients` | — | DISCARDED | Replaced by `ConnectionManager` |
| `[80.27, 13.08]` Chennai fallback | — | DISCARDED | Replaced by explicit `location_unavailable_result()` |
| synchronous in-request agent pipeline | — | DISCARDED | Replaced by queue + background worker (202 response) |
| `app/geocode.py` implicit hot-path call | — | DISCARDED | Clustering no longer depends on a network call |

## Deferred features (Phase 31) — interface exists, not implemented

| Feature | Where the interface lives | Why deferred |
|---|---|---|
| OR-Tools VRP optimization | `AllocationStrategy` (AG-5) | `ortools` not installed; `GreedyFallback` is the only strategy |
| Real satellite/CV damage detection | `DeterministicExposureEstimator` (AG-2) | No imagery pipeline; heuristic is explicitly labelled |
| Real road-network routing (OSRM/Valhalla) | `RouteProvider` (AG-6), `ROUTING_PROVIDER`/`OSRM_URL` config | No OSRM instance available |
| Vector-store RAG | `VectorStore` (AG-7) | `KeywordRetriever` dev fallback only |
| Drone ingestion | — | No V1 normalizer ever existed |
| Social media ingestion | — | No V1 normalizer ever existed |
| GIS ingestion | — | No V1 normalizer ever existed |
| Predictive impact modeling | — | Needs a weather/trend model not in scope |
| Kafka | `QueueService` (Redis-list-backed today) | Not required at this scale; interface is swappable |
| Kubernetes horizontal scaling | — | Deployment concern, not exercised |
| `event_sources` provenance rows | `models/incident.py::EventSource` | Table exists; ingestion doesn't populate it yet |
| `recommendation_evidence` rows | `models/recommendation.py::RecommendationEvidence` | Table exists; evidence lives on `AgentResult`/`Recommendation.reasoning` today |
| `resource_allocations` / `routes` / `route_status` rows | respective models | Tables exist; AG-5/AG-6 decisions live in `Recommendation.details` JSON, not a normalized row, today |
| Citizen reports list + incident severity-grid API | — | No V2 endpoint built; frontend calls left pointed at V1 paths with a documented gap |
| V2 JSON metrics endpoint matching V1's `/metrics` shape | `api/health.py` (Prometheus text today) | Format change, not just a path — needs its own endpoint or a frontend Prometheus parser |

## Environment facts (do not re-verify without new evidence)

- Docker daemon unavailable (`docker ps` fails) → PostgreSQL/PostGIS and
  real Redis are **NOT VERIFIED** throughout this migration. SQLite +
  `fakeredis` back all 70 automated backend-v2 tests.
- `ortools` not installed → AG-5 optimizer strategy is **DEFERRED**.
- V1 (`backend/`) is untouched: 74 tests, all still passing, unmodified.
