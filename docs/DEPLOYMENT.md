# Deployment

Target: **backend-v2** (FastAPI + Postgres/PostGIS + Redis) and **frontend-next**
(Next.js). `backend/` (V1) and `optimus-the-ai-platform-to-build-and-ship/` /
`stitch_eoc_command_console/` (design references) are not deployed.

## Quick path (Docker Compose)

```bash
cp deploy/.env.example deploy/.env        # fill in every value
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env run --rm seed   # first run only
```

`seed` prints the generated device secrets once if you did not supply them.
Put TLS in front (reverse proxy / LB): the browser must reach the frontend over
https and the API over https/wss (`/ws/alerts`).

## Configuration

| Where | Variable | Notes |
|---|---|---|
| frontend (build) | `NEXT_PUBLIC_API_BASE` | Public backend URL. **Inlined at build time** — rebuild to change. |
| frontend (build) | `NEXT_PUBLIC_MAP_STYLE_URL` | Optional MapLibre style URL. Empty = CARTO public dark style (third-party tiles: check its terms/availability, or self-host). |
| frontend (runtime) | `BACKEND_URL` | Internal URL the Next server uses for its `/api/*` proxies. |
| frontend (runtime) | `CITIZEN_DEVICE_ID` / `CITIZEN_DEVICE_SECRET` | Credential for public citizen chat/report. Server-only. |
| frontend (runtime) | `DEMO_INGEST_ENABLED` | Keep `false` in production. |
| backend | `APP_ENV=production`, `JWT_SECRET` (≥32 chars), `DATABASE_URL`, `REDIS_URL`, `QUEUE_BACKEND=redis`, `CORS_ORIGINS` | `CORS_ORIGINS` must be the exact public frontend origin. |
| backend | `GROQ_API_KEY` | Optional. Without it agents use rule-based logic (AG-1 shows "rule-based"), and citizen answers fall back to the built-in English/Hindi/Tamil retrieval. |

## Constraints to know about

- **Run one backend process.** The agent queue worker runs inside the API
  process (`app/main.py` lifespan); do not scale it horizontally yet.
- **Redis is mandatory** (no silent in-memory fallback by design).
- **Agency visibility:** situation-level outputs (AG-1, AG-2, AG-8) are
  explicitly flagged `is_global` and visible to every authenticated user (any
  OPERATOR can decide them, VIEWERs cannot). Resource-targeted outputs
  (AG-3..AG-6) are visible only to the owning agency and ADMINs. A recommendation
  whose agency cannot be resolved stays ADMIN-only (it is never treated as global).
- **Ambulances** are a real table (`ambulances`); the dev seed (`SEED_DEMO=1`)
  creates two per hospital. Production deployments must load their own fleet.
- **Accounts:** `/signup` and `/forgot-password` create *requests*; an ADMIN
  approves them under **Access** in the console and receives a one-time
  temporary password to hand over out-of-band (no email service is assumed).
  The user must change it at first sign-in. The public request endpoints are
  reachable only through the Next proxy (citizen device credential) and are
  rate-limited per IP there; behind multiple frontend instances add a shared
  limiter at the gateway.
- **Predictive impact** (`GET /incidents/{id}/forecast`) is a labelled linear
  trend over water-level readings, not a hydrological model.
- **Citizen assistant languages:** Hindi and Tamil answers come from a
  machine-drafted translated corpus (`app/agents/citizen_assistance/i18n.py`).
  **Have a native speaker review it before real use.** Other languages need
  `GROQ_API_KEY`; without it the reply is English and the UI says so.
- Browser session: JWT in `localStorage`; the WebSocket token travels as a query
  parameter (browsers cannot set WS headers). Terminate TLS and avoid logging
  query strings at the proxy.

## Verification done in development

`python -m pytest tests` (backend-v2), `alembic upgrade head` on SQLite,
`npx tsc --noEmit`, `npm run lint`, `npm run build`, and a headless-browser
pass over every console route against a live backend. Not verified: Docker
image builds, PostgreSQL migration run, multi-instance behaviour.
