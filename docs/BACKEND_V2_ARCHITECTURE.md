# Backend V2 Architecture

See `docs/BACKEND_V2_MIGRATION_ANALYSIS.md` for the full V1 read and the
rationale behind every deviation from the originally suggested tree;
`docs/BACKEND_V2_MIGRATION.md` for current build/test status.

## Request flow

```
Device/API client
  -> api/ingestion.py          (device auth, Pydantic validation)
  -> ingestion/service.py      (normalize -> persist Event -> associate Incident)
  -> infrastructure/queue.py   (enqueue; HTTP returns 202 here)
  ----------------------------------------------------------------
  (background worker thread, started in main.py's lifespan)
  -> orchestration/graph.py    (run_for_event: builds initial GraphState)
  -> LangGraph StateGraph      (router.py order, conditions.py gating)
       AG-1 -> AG-2 -> AG-3 -> AG-4 -> AG-5 -> AG-6 -> AG-8
       each node (execution.py):
         - builds AgentContext from the current Redis blackboard snapshot
         - agent.run(context)                         [agents/base.py]
         - blackboard.merge(...)                       [orchestration/state.py]
         - AgentRun/AgentHealth persisted              [services/agent_health_service.py]
         - Recommendation persisted                    [recommendations/service.py]
         - AuditLog persisted                          [services/audit_service.py]
         - Alert published if severity-worthy          [services/alert_service.py]
  -> recommendations/conflict.py  (ConflictDetector over the final blackboard)
  -> incidents/service.py         (severity updated from AG-1's result)
  ----------------------------------------------------------------
Human (api/recommendations.py: POST .../decide)
  -> recommendations/service.py (approve | reject | override, agency-checked)
  -> AuditLog
Alert published -> infrastructure/websocket.py pub/sub bridge
  -> ConnectionManager.broadcast (agency-filtered) -> authenticated /ws/alerts clients
```

AG-7 (citizen chat) is not in the chain above — `api/citizen.py` calls
`CitizenAssistant` directly, request/response, per CLAUDE.md.

## Layering

- `api/` — FastAPI routers only: parse request, call a service, map the
  result to a response schema. No business logic.
- `agents/` — one subpackage per agent (`agent.py` + `schemas.py`; AG-1 also
  has `rules.py`/`prompts.py` since it's the only agent with real content
  there). Agents never touch the DB or Redis directly — they read an
  `AgentContext` built by the caller and return an `AgentResult`.
- `orchestration/` — `router.py` (fixed agent order), `conditions.py`
  (which agents run for a given event), `execution.py` (per-agent node
  body: context build, run, persist side effects), `graph.py` (LangGraph
  wiring + the background worker loop), `state.py` (the Redis blackboard).
- `incidents/`, `recommendations/` — persistent services + typed schemas
  for their respective domains, including clustering and conflict
  detection.
- `services/` — cross-cutting persistent services with no natural home in
  a single domain package: resources, audit, alerts, agent health, routing.
- `infrastructure/` — DB engine/session, Redis client, queue, WebSocket
  connection manager + pub/sub bridge, LLM client.
- `security/` — JWT, password hashing, RBAC (`require_role`,
  `require_permission`), agency isolation (`require_agency_access`), device
  authentication.
- `models/` — SQLAlchemy ORM (the 20 tables in Phase 2).
- `schemas/` — top-level Pydantic contracts that don't belong to one
  domain package (currently just `auth.py`); domain-specific request/
  response schemas live next to their domain (`incidents/schemas.py`,
  `recommendations/schemas.py`, `ingestion/schemas.py`,
  `agents/*/schemas.py`).
- `observability/` — structured logging correlation fields, Prometheus
  metrics.

## Deliberate deviations from the originally suggested tree

Recorded once here instead of scattered across docstrings:

1. **Sync SQLAlchemy 2.0 + psycopg 3, not async.** Agents are lightweight,
   `fakeredis`/SQLite testing is simpler, and FastAPI runs `def` endpoints
   in a threadpool automatically. The WebSocket handler and the queue
   worker are the only async-vs-sync boundaries, and both explicitly
   avoid blocking the event loop (`asyncio.to_thread` for the sync Redis
   pub/sub read).
2. **`app/geo.py`** is one small module (ported from V1 `geo_utils.py`)
   instead of scattered geo helpers.
3. **No `drone`, `social`, `gis` normalizers or ingestion endpoints.** No
   V1 implementation exists for any of them; exposing an endpoint with no
   real normalizer behind it would violate the spec's own "don't ship
   fake implementations" rule.
4. **PostGIS `geom` columns are added by the Alembic migration on the
   `postgresql` dialect only.** The ORM models use plain `latitude`/
   `longitude` floats as the portable source of truth; SQLite tests never
   touch a PostGIS type. See `migrations/versions/*_initial_schema.py`.
5. **Enum columns use `sqlalchemy.Enum(..., native_enum=False)`**, not
   `String`. A plain `String` column does not coerce reads back to the
   Python enum member — found and fixed as a real bug mid-migration (see
   `docs/BACKEND_V2_MIGRATION.md`).
