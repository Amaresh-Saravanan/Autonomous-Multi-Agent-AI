# Autonomous Multi-Agent AI Platform — Disaster Response

Autonomous multi-agent disaster-response platform. Synthetic or real sensor
events (IoT, weather, satellite, citizen reports) flow through normalizers →
a fixed chain of 8 AI agents orchestrated with LangGraph → recommendations
carrying mandatory evidence and rationale → a live map dashboard, over HTTP
and WebSocket. Agents only ever recommend; a human operator approves or
rejects every recommendation before it takes effect.

The 8 agents (`backend-v2/app/agents/`), run in order on every event:

1. **Disaster Assessment** (AG-1) — defines the incident
2. **Damage Assessment** (AG-2)
3. **Rescue Planning** (AG-3)
4. **Medical Coordination** (AG-4)
5. **Resource Allocation** (AG-5)
6. **Route Optimization** (AG-6)
7. **Citizen Assistance** (AG-7) — request/response citizen chat, not part of the event chain
8. **Situational Intelligence** (AG-8) — summarizes the whole incident, runs last

Docs: `docs/PRD.md` (requirements), `docs/TDD.md` (architecture/stack),
`docs/ARCHITECTURE.md`, `docs/UX_DESIGN.md` (dashboard design), `docs/RUNBOOK.md`
(day-to-day operation). `docs/archive/` holds superseded migration-era docs
(the backend-v2 migration write-ups, old phase trackers) kept for history.

## Run it

### backend-v2 (FastAPI + Postgres/PostGIS + Redis)

With Docker (brings up Postgres, Redis, and the API together; the API
container runs migrations and starts itself):

```bash
cd backend-v2
docker compose up -d
```

Without Docker (point `DATABASE_URL` / `REDIS_URL` at your own Postgres/Redis,
or rely on the dev fallbacks — see `backend-v2/app/config.py`):

```bash
cd backend-v2
python -m pip install -r requirements.txt
alembic upgrade head
SEED_ADMIN_EMAIL=you@agency.org python -m app.seed   # first run only; prints generated secrets once
python -m uvicorn app.main:app --reload --port 8001
python -m pytest tests/ -v
```

Set `GROQ_API_KEY` to enable LLM-assisted reasoning; every agent has a
rule-based fallback, so the platform runs with nothing but Python installed.

### frontend-next (Next.js + TypeScript + Tailwind)

```bash
cd frontend-next
npm install
npm run dev      # http://localhost:3000, connects to backend-v2
```

For a production-style deploy (Docker Compose, TLS, env var reference), see
`docs/archive/DEPLOYMENT.md`.

## Folder map

| Path | What it is |
|---|---|
| `backend-v2/` | Current backend — FastAPI app (`app/agents/`, `app/orchestration/`, `app/security/`, `app/api/`), Alembic migrations, tests |
| `backend/` | **Legacy v1** backend, kept in place as a reference only — not deployed, not actively developed |
| `frontend-next/` | Current frontend — Next.js console/dashboard |
| `deploy/` | Production Docker Compose + env template |
| `docs/` | Live design/requirements docs (PRD, TDD, ARCHITECTURE, RUNBOOK, UX_DESIGN) |
| `docs/design/` | Standalone design references (e.g. the Kinetic Command mockup) |
| `docs/archive/` | Superseded migration-era docs, kept for history |
