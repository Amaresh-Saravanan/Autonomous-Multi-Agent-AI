# Backend V2 ↔ Frontend Compatibility (Phase 25)

Source: `frontend-next/lib/api.ts` + `frontend-next/lib/operations-context.tsx`
against `backend/app/main.py` (V1) and `backend-v2/app/api/*.py` (V2).
"Frontend change" column marks what was actually edited in this pass;
"DEFERRED" means the V2 backend endpoint doesn't exist yet, so the
frontend call is left pointed at its old path rather than invented against
nothing.

| Frontend call | V1 endpoint | V2 endpoint | Request/response changes | Frontend change |
|---|---|---|---|---|
| `login()` | `POST /auth/login` `{username,password}` | `POST /api/v1/auth/login` `{email,password}` | field renamed `username`→`email` (Pydantic `EmailStr`) | **Applied** |
| `fetchResources()` | `GET /resources` | `GET /api/v1/resources` | same shape (`hospitals/shelters/teams/ambulances/supplies`) | **Applied** (path only) |
| `fetchRecommendations()` | `GET /recommendations` | `GET /api/v1/recommendations` | V2 adds `?incident_id=` filter (unused by frontend today, optional) | **Applied** (path only) |
| `fetchIncidents()` | `GET /incidents` | `GET /api/v1/incidents` | same shape | **Applied** (path only) |
| `fetchIncidentState()` | `GET /incidents/{id}` | `GET /api/v1/incidents/{id}` | same shape | **Applied** (path only) |
| `fetchAudit()` | `GET /audit` | `GET /api/v1/audit` | same shape, ADMIN-only on both | **Applied** (path only) |
| `decideRecommendation()` | `POST /recommendations/{id}/approve` or `/reject` | `POST /api/v1/recommendations/{id}/decide` `{decision}` | one endpoint replaces two; `decision` also accepts `"override"` (not yet wired in the UI — no override control exists) | **Applied** |
| `ingestWaterLevel()` | `POST /ingest/iot`, open, returns `{event_id, incident_id, recommendations}` synchronously | `POST /api/v1/ingestion/iot`, device-authenticated, returns **202** `{event_id, incident_id, status:"accepted"}` | **behavioral**: no recommendations in the response; requires `X-Device-Id`/`X-Device-Secret` headers instead of a user bearer token | **Applied** — see below |
| WS `/ws/alerts` | open, broadcasts `{incident_id, recommendations[]}` to every client | `wss://.../ws/alerts?token=<JWT>`, agency-filtered, pushes `{alert_id, incident_id, level, message}` | **behavioral**: auth required; payload no longer carries recommendations inline (agency filtering means not every client needs/gets every incident) | **Applied** |
| `postCitizenChat()` | `POST /citizen/chat`, open | `POST /api/v1/citizen/chat`, device-authenticated | same request/response shape, now needs device headers | Path updated; **device-auth not wired** (DEFERRED — no demo credential plumbed into the chat widget yet) |
| `fetchMetrics()` | `GET /metrics` → JSON `MetricsSummary` | `GET /api/v1/health/metrics` → Prometheus text format | **format change**, not just a path change | **DEFERRED** — left pointed at old path; needs a new JSON-shaped endpoint or a frontend Prometheus parser, neither built here |
| `fetchCitizenReports()` | `GET /citizen/reports` | *(no V2 endpoint yet)* | citizen_reports are persisted (Phase 9) but no list API exists | **DEFERRED** — left pointed at V1 path |
| `fetchSeverityGeojson()` | `GET /incidents/{id}/severity` | *(no V2 endpoint yet)* | severity grid service not ported to V2 | **DEFERRED** — left pointed at V1 path |

## Required behavioral change: ingestion result surfacing

V1: `POST /ingest/iot` ran the whole agent chain in-request and returned
recommendations synchronously. V2 returns 202 immediately; the chain runs
on a background queue worker. The frontend's demo ingestion flow
(`IngestForm` → `onIngested`) was changed to:

1. `ingestWaterLevel()` returns only `{event_id, incident_id, status}`.
2. `onIngested(incidentId)` sets the current incident and refreshes
   severity/incident-state/citizen-reports immediately (so the map centers
   on the right incident), but does **not** merge any recommendations —
   there aren't any yet.
3. When the agent chain finishes, the orchestrator publishes an alert; the
   authenticated WS delivers `{incident_id, ...}`; the handler calls
   `refreshRecommendations()` (a new `GET /api/v1/recommendations` fetch)
   instead of reading recommendations out of the socket payload.

This matches the required flow: *Demo ingestion → HTTP 202 → event accepted
→ processing occurs → WebSocket receives result → UI updates* — the UI
updates on the WS signal via a fetch, not an inline payload.

## Required behavioral change: WebSocket authentication

Browsers cannot set a custom `Authorization` header on a WebSocket
handshake, so the same JWT from `/api/v1/auth/login` is passed as a query
parameter: `wss://.../ws/alerts?token=<JWT>`. The backend's `/ws/alerts`
decodes it the same way `require_user` does for HTTP, then filters every
broadcast to the connecting user's agency (ADMIN sees everything).

## Device credentials in a browser (ingestion demo button only)

V2 gates all ingestion (including the citizen chat) behind device
credentials (Phase 7), not user JWTs — closing V1 problems #10/#11 (open
ingest, open citizen chat). The "Simulate water-level reading" demo button
is the **one** place a device secret is read from `NEXT_PUBLIC_*` env vars
on the client. This is acceptable only because:

- it is explicitly a labelled demo/simulation control, not a real sensor, and
- a real IoT sensor should embed its own device secret at the hardware/
  firmware layer, never ship one inside browser JavaScript served to end
  users.

The citizen chat widget's device-auth wiring was **not** completed in this
pass (no demo device credential is plumbed into `postCitizenChat()` yet) —
tracked as DEFERRED above, consistent with not inventing frontend behavior
against a half-wired auth path.

## Not changed

Everything else (login form markup, dashboard layout, map rendering,
recommendation/incident panels, citizen report panel, severity overlay) is
untouched — per the migration rules, this pass updates only what V2's API
semantics require, not a UI redesign.
