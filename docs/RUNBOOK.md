# Runbook

How to run, log in, and operate the backend locally. Generated from the final Phase 3 state — see `docs/MIGRATION_TRACKER.md` for build history and `docs/superpowers/specs/2026-08-13-rbac-design.md` for the auth design.

## Setup

```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env   # optional: fill in GROQ_API_KEY / REDIS_URL / JWT_SECRET
python -m uvicorn app.main:app --reload   # serves on :8000
```

Nothing above is required to run — `GROQ_API_KEY` unset falls back to rule-based agent reasoning, `REDIS_URL` unset falls back to an in-memory blackboard, `JWT_SECRET` unset falls back to a dev-only default (logs a warning, never use outside local dev).

Frontend: open `frontend/index.html` directly in a browser (no build step, no dev server — it's a `file://` page that fetches `http://localhost:8000`).

## Running tests

```bash
cd backend
python -m pytest tests/ -v          # full suite
python -m pytest tests/test_auth.py -v   # single file
```

Load test (needs the server running separately, not part of the pytest suite):

```bash
python -m uvicorn app.main:app --port 8000 &   # start server in background
python scripts/load_test.py                     # fires concurrent requests, prints p50/p95/p99
```

## Logging in

`POST /auth/login` with a username/password from the seed user list below returns a JWT (`{"access_token": "...", "token_type": "bearer"}`, 4-hour TTL). Send it back as `Authorization: Bearer <token>` on any gated route.

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "bob_operator", "password": "operator-pass"}'
```

### Seed users (`backend/app/auth.py`, dev/demo only — not real credentials)

| Username | Password | Role | Agency |
|---|---|---|---|
| `alice_admin` | `admin-pass` | admin | city_emergency_mgmt |
| `bob_operator` | `operator-pass` | operator | city_emergency_mgmt |
| `carol_viewer` | `viewer-pass` | viewer | regional_health_dept |
| `dave_operator` | `operator-pass2` | operator | regional_health_dept |

Role hierarchy: `admin > operator > viewer` — a higher role satisfies any lower role's gate (e.g. an operator token works anywhere a viewer token does).

## API reference

| Endpoint | Method | Required role | Description |
|---|---|---|---|
| `/health` | GET | open | Liveness check + whether the blackboard is Redis-backed |
| `/auth/login` | POST | open | Exchange username/password for a JWT |
| `/metrics` | GET | operator+ | Request counts/latency per route (tracker 3.8) + recommendation acceptance rate |
| `/resources` | GET | viewer+ | Hospitals, shelters, teams, ambulances registry |
| `/ingest/{source_type}` | POST | open | Ingest a raw event (`iot`, `weather`, `satellite`, `citizen`); runs the agent chain, returns recommendations |
| `/incidents/{incident_id}` | GET | viewer+ | Full blackboard state for an incident (per-agent latest output + any surfaced conflicts) |
| `/incidents/{incident_id}/severity` | GET | viewer+ | Severity grid as GeoJSON |
| `/recommendations` | GET | viewer+ | List recommendations (optional `?status=` filter); agency-scoped for non-admin users (tracker 3.5) |
| `/recommendations/{rec_id}/approve` | POST | operator+ | Approve a recommendation (audited with the real authenticated username) |
| `/recommendations/{rec_id}/reject` | POST | operator+ | Reject a recommendation (audited) |
| `/citizen/chat` | POST | open | Citizen-facing chat (multilingual, RAG-assisted — tracker 3.2); citizens aren't platform users |
| `/ws/alerts` | WebSocket | open | Live push of new recommendations to connected dashboards — not yet auth-gated, a known gap (see Known Gaps below) |

## Known gaps (honest, not silently closed)

- **`frontend/index.html` has no login flow yet.** Its fetches send no `Authorization` header, so every gated GET now returns 401 from the browser. The dashboard needs a login screen + token storage before it works against this backend again — tracked as a follow-up, out of scope for Phase 3's backend-focused items.
- **`GET /ws/alerts` is unauthenticated**, outside the RBAC endpoint matrix — anyone can connect and receive live recommendation pushes. Deferred, not forgotten.
- **Audit logging covers only approve/reject** (`_decide()` in `app/main.py`) — tracker 1.11 ("audit log wired to all state changes") remains open; other state-changing calls (e.g. `/ingest`) aren't individually audited yet.
- **2.4** (real OSRM routing) and **2.10** (predictive impact) remain accepted/deferred debt from Phase 2 — see the Decisions Log in `docs/MIGRATION_TRACKER.md`.
- **3.7's load test found a real signal**: p95 latency ~2.25s at 50 concurrent requests against the single-process dev server, failing its own 2000ms sanity threshold — worth revisiting if this needs to be proven at the PRD's actual 10k-sensor/100-operator target.
