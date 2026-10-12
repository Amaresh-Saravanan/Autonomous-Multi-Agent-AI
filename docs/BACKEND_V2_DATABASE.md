# Backend V2 Database

SQLAlchemy 2.0, sync, `psycopg[binary]` for PostgreSQL in production,
SQLite for tests (`sqlite:///...`). Alembic migration:
`migrations/versions/e7f4e236fb70_initial_schema.py`.

## Tables (20)

| Table | Model | Notes |
|---|---|---|
| `agencies` | `security.Agency` | |
| `users` | `security.User` | role: ADMIN/OPERATOR/VIEWER |
| `permissions`, `role_permissions` | `security.Permission`, `RolePermission` | schema exists; runtime checks use the code-level `ROLE_PERMISSIONS` map in `security/permissions.py`, not a DB query, since permissions are fixed per role rather than dynamically assigned |
| `devices` | `security.Device` | ingestion/citizen-chat credentials, scoped to `source_type` + `agency_id` |
| `incidents` | `incident.Incident` | `location_state` (exact/approximate/unknown) gates whether `latitude`/`longitude` are usable |
| `events` | `incident.Event` | raw ingested payload + its own `location_state` |
| `event_sources` | `incident.EventSource` | provenance (device/channel); not yet populated by `ingestion/service.py` — DEFERRED |
| `recommendations` | `recommendation.Recommendation` | `target_agency_id` NULL is never "visible to everyone" (enforced in `recommendations/service.py`, not the DB) |
| `recommendation_evidence` | `recommendation.RecommendationEvidence` | schema exists; not populated yet — evidence today lives on `Recommendation.reasoning`/agent's own `AgentResult.evidence` list, not broken out per-row — DEFERRED |
| `resources`, `resource_allocations` | `resource.Resource`, `ResourceAllocation` | `resource_allocations` schema exists; not yet written by AG-5 (AG-5's allocation decision lives in the Recommendation `details`, not a persisted allocation row) — DEFERRED |
| `shelters`, `hospitals`, `rescue_teams` | `resource.*` | read by `services/resource_service.py` into the plain-dict snapshot agents consume |
| `routes`, `route_status` | `route.Route`, `RouteStatusEvent` | schema exists; AG-6/`RoutingService` returns a `RouteResult` today but nothing persists it to these tables yet — DEFERRED |
| `citizen_reports` | `citizen.CitizenReport` | written by the citizen ingestion path with a verification/trust score |
| `alerts` | `alert.Alert` | dedup via persisted `dedup_key`, not an in-memory dict |
| `audit_logs` | `audit.AuditLog` | append-only at the application level (no update/delete method anywhere) |
| `agent_runs`, `agent_health` | `agent.AgentRun`, `AgentHealth` | one row per agent execution + one rolling-stats row per agent |

## Conventions

- UUID primary keys (`sqlalchemy.Uuid`, native on Postgres, portable
  elsewhere).
- Timezone-aware `DateTime` everywhere a timestamp exists.
- Enum columns use `Enum(..., native_enum=False)` — stored as `VARCHAR` on
  both dialects, and (unlike a plain `String` column) coerces reads back
  to the Python enum member. Found as a real bug mid-migration; see
  `docs/BACKEND_V2_MIGRATION.md`.
- Indexes on every foreign-key-ish lookup column (`incident_id`,
  `agency_id`, `timestamp`, `status`, `target_agency_id`, etc.) per the
  spec's Phase 2 list.

## PostGIS

Production-only. The Alembic migration adds a `geom geography(Point,4326)`
column + GiST index + a sync trigger (keeping it in step with
`latitude`/`longitude` on insert/update) to `incidents`, `events`,
`shelters`, `hospitals`, `rescue_teams`, `citizen_reports`, gated on
`bind.dialect.name == "postgresql"`. Nothing in the ORM or application
code queries `geom` yet — it exists for future spatial queries
(`ST_DWithin` clustering, etc.) without having distorted the portable
schema tests run against. **NOT VERIFIED against a real PostgreSQL
instance** — Docker/Postgres are unavailable in this environment; the
migration's `upgrade`/`downgrade` were verified against SQLite only (the
PostGIS block is a no-op there by design).
