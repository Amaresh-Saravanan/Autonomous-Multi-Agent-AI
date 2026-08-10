# Technical Design Document (TDD)
## Autonomous Multi-Agent AI Platform for Disaster Response

**Version:** 1.0
**Date:** 2026-07-24
**Companion to:** PRD.md

---

## 1. Architecture Overview

```
                        ┌─────────────────────────────────────────┐
                        │           EOC Dashboard (Next.js)        │
                        │  Map · Recommendation feed · Alerts ·    │
                        │  Citizen chat · RBAC views               │
                        └───────────────▲─────────────────────────┘
                                        │ REST + WebSocket
                        ┌───────────────┴─────────────────────────┐
                        │        API Gateway (FastAPI)             │
                        │  Auth (RBAC) · WS hub · Audit log        │
                        └───────────────▲─────────────────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             │              Agent Orchestrator (LangGraph)          │
             │   Blackboard state · scheduling · conflict surfacing │
             └───┬───────┬───────┬───────┬───────┬──────┬───────┬───┘
                 │       │       │       │       │      │       │
             ┌───▼─┐ ┌───▼─┐ ┌───▼─┐ ┌───▼─┐ ┌──▼──┐ ┌─▼───┐ ┌─▼────┐
             │Disas│ │Damag│ │Rescu│ │Route│ │Resrc│ │Medic│ │Situat│  ...+Citizen
             │ AG-1│ │ AG-2│ │ AG-3│ │ AG-6│ │AG-5 │ │AG-4 │ │AG-8  │
             └───┬─┘ └───┬─┘ └───┬─┘ └───┬─┘ └──┬──┘ └─┬───┘ └─┬────┘
                 └───────┴───────┴───┬───┴──────┴──────┴───────┘
                                     │ tools
             ┌───────────────────────▼───────────────────────────┐
             │     Shared Services: geospatial (PostGIS),         │
             │     routing (OSRM/Valhalla), vector store (RAG),   │
             │     optimization solver (OR-Tools)                 │
             └───────────────────────▲───────────────────────────┘
                                     │
             ┌───────────────────────┴───────────────────────────┐
             │       Ingestion & Streaming (Kafka / Redis Streams)│
             │  Normalizers → common event schema → geo-index     │
             └──┬────┬────┬─────┬──────┬────────┬─────────────────┘
                │    │    │     │      │        │
            Satellite Drone IoT Weather Social  GIS
```

### 1.1 Design principles
- **Event-driven.** Everything reacts to normalized events on the bus.
- **Blackboard collaboration.** Agents read/write shared state; no tight coupling.
- **Human-in-the-loop.** Agents emit *recommendations*; execution needs approval.
- **Evidence-first.** Every agent output references the source events it used.
- **Graceful degradation.** A dead source/agent reduces confidence, not availability.

---

## 2. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Agent reasoning | **Groq API (Mixtral-8x7B)** — free tier, hosted | Zero cost, sub-second inference, no local install needed for teammates |
| Vision (AG-1 only) | **Together.ai (LLaVA-1.5-7B)** — free credits | Multimodal (satellite/drone image) reasoning without a paid vendor |
| Agent orchestration | **LangGraph** (Python) | Graph-based multi-agent state machines, blackboard fits naturally |
| Backend API | **FastAPI** (Python) | Async, WebSocket, fast to build |
| Streaming / bus | **Kafka** (prod) / **Redis Streams** (dev/MVP) | Durable event streaming; Redis for low-friction start |
| Geospatial DB | **PostgreSQL + PostGIS** | Standard for geo queries |
| Time-series (sensors) | **TimescaleDB** (Postgres ext.) | Same DB engine, sensor time-series |
| Vector store (RAG) | **pgvector** | Reuse Postgres; avoid extra infra |
| Routing engine | **OSRM** or **Valhalla** | Self-host road routing w/ blocked-road avoidance |
| Optimization | **Google OR-Tools** | Resource allocation & vehicle routing (VRP) |
| Frontend | **Next.js + React + TypeScript** | SSR dashboard, App Router |
| Map | **MapLibre GL** (+ Mapbox tiles optional) | Open, layered vector maps |
| Realtime UI | **WebSocket** (FastAPI) | Push alerts/updates |
| Auth | **OAuth2 / JWT** + RBAC | Agency + role scoping |
| Deploy | **Docker Compose** (MVP) → **Kubernetes** (scale) | Start simple, scale later |

> `ponytail:` Redis Streams + Docker Compose for MVP; upgrade to Kafka + K8s only
> when throughput/scale actually demands it. Don't stand up Kafka on day one.

### 2.1 Per-agent model assignment (free, cloud-hosted — no local install)

| Agent | Model | Service | Cost |
|---|---|---|---|
| AG-1 Disaster Assessment | `llava-1.5-7b` (vision) + `mixtral-8x7b-32768` (reasoning) | Together.ai + Groq | Free |
| AG-2 Damage Assessment | `mixtral-8x7b-32768` | Groq | Free |
| AG-3 Rescue Planning | `mixtral-8x7b-32768` | Groq | Free |
| AG-4 Medical Coordination | `mixtral-8x7b-32768` | Groq | Free |
| AG-5 Resource Allocation | `mistral-7b-instruct` (formats input for OR-Tools solver) | Groq | Free |
| AG-6 Route Optimization | `mistral-7b-instruct` (formats constraints; OSRM does the actual routing) | Groq | Free |
| AG-7 Citizen Assistance | `mixtral-8x7b-32768` (multilingual chat + RAG) | Groq | Free |
| AG-8 Situational Intelligence | `mixtral-8x7b-32768` (32k context for summarization) | Groq | Free |

**Why cloud-hosted free APIs over local Ollama:** teammates and reviewers hit a
shared HTTPS endpoint — no GPU, no local model download, no "works on my
machine." Groq's free tier is rate-limited (not credential-limited); Together.ai
gives $25/mo free credit for the one multimodal model Groq doesn't serve.

> Exact free-tier limits and model names should be re-verified against Groq's
> and Together.ai's current docs before locking into production — provider
> free-tier terms change over time.

---

## 3. Data Model

### 3.1 Common Event Schema (all sources normalize to this)
```json
{
  "event_id": "uuid",
  "source_type": "satellite|drone|iot|weather|social|gis|citizen",
  "source_id": "string",
  "timestamp": "ISO-8601",
  "geo": { "type": "Point|Polygon", "coordinates": [...] },
  "payload": { "...source-specific..." },
  "confidence": 0.0,
  "ingested_at": "ISO-8601"
}
```

### 3.2 Core tables (PostGIS)
- `events` — normalized events (geo-indexed, GIST).
- `sensors` — IoT registry (location, type, status).
- `incidents` — clustered/confirmed disaster incidents (agent-created).
- `severity_grid` — H3/geohash cells with computed severity + timestamp.
- `recommendations` — agent outputs (agent_id, incident_id, action, evidence[], confidence, status).
- `resources` — hospitals, shelters, teams, vehicles, supplies (capacity, location, status).
- `routes` — computed routes (geometry, hazards avoided, valid_until).
- `citizen_reports` — reports + verification status + trust score.
- `audit_log` — immutable append-only (actor, action, target, timestamp, before/after).
- `users`, `roles`, `agencies` — RBAC.

### 3.3 Blackboard (agent shared state)
Held in Redis (hot) + persisted to Postgres. Keyed by `incident_id`. Structure:
```
incident:{id} → {
  disaster: {...},      // AG-1 output
  damage: {...},        // AG-2
  rescue_plan: {...},   // AG-3
  medical: {...},       // AG-4
  resources: {...},     // AG-5
  routes: {...},        // AG-6
  situation: {...},     // AG-8 rolling summary
  conflicts: [...],     // surfaced disagreements
  last_updated: ...
}
```

---

## 4. Agent Design

### 4.1 Agent contract (uniform interface)
```python
class Agent(Protocol):
    id: str
    def triggers(self) -> list[Trigger]: ...        # what events wake it
    def run(self, ctx: Blackboard, events: list[Event]) -> Recommendation: ...
    #   MUST return: action, evidence (list of event_ids), confidence, rationale
```

Every `Recommendation` includes `evidence[]` and `rationale` (satisfies DS-7, AC-3).
Confidence below threshold → flagged, not auto-surfaced as high-priority.

### 4.2 Per-agent detail

| Agent | Key inputs | Tools | Output |
|---|---|---|---|
| **AG-1 Disaster Assessment** | satellite tiles, IoT, weather, social | LLaVA-1.5-7B (vision) + Mixtral-8x7B (reasoning), anomaly detection | disaster type, severity grid, confidence |
| **AG-2 Damage Assessment** | pre/post imagery, GIS building/pop layers | Mixtral-8x7B, change-detection, pop-density lookup | damaged structures, affected population estimate |
| **AG-3 Rescue Planning** | incidents, damage, resources | Mixtral-8x7B, priority scoring, team assignment | ranked rescue task list w/ team assignment |
| **AG-4 Medical Coordination** | casualties, hospital capacity, ambulances | Mixtral-8x7B, capacity matching, dispatch | hospital allocation + ambulance dispatch plan |
| **AG-5 Resource Allocation** | needs, inventory, shelters | Mistral-7B (problem formulation) + OR-Tools (assignment/VRP) | allocation plan (what, where, how much) |
| **AG-6 Route Optimization** | road GIS, blocked roads, traffic, hazards | Mistral-7B (constraint formatting) + OSRM w/ dynamic edge weights | evacuation + vehicle routes (GeoJSON) |
| **AG-7 Citizen Assistance** | citizen queries, verified status | Mixtral-8x7B chat + translation + RAG on official guidance | multilingual answers; ingests reports as events |
| **AG-8 Situational Intelligence** | entire blackboard | Mixtral-8x7B summarization (32k context) | rolling explainable status + top recommendations |

### 4.3 Orchestration (LangGraph)
- Graph nodes = agents; edges = data dependencies.
- New event → orchestrator matches triggers → schedules affected agents.
- AG-1 typically runs first (defines incident); AG-8 runs last (summarizes).
- **Conflict handling:** if two agents write incompatible recommendations for the
  same target, orchestrator writes both to `conflicts[]` and flags for human (AC-4).
- Runs on a loop + on-trigger; AG-8 re-summarizes on each cycle.

---

## 5. APIs (representative)

```
POST /ingest/{source_type}          # push normalized/raw event
GET  /incidents                     # active incidents
GET  /incidents/{id}                # full blackboard view
GET  /incidents/{id}/severity       # severity grid (GeoJSON)
GET  /recommendations?status=pending
POST /recommendations/{id}/approve  # human decision (audited)
POST /recommendations/{id}/reject
GET  /routes/{incident_id}          # computed routes
POST /citizen/chat                  # multilingual assistant
POST /citizen/report                # citizen report → verification pipeline
GET  /alerts/stream                 # WebSocket: live alerts + updates
```

All state-changing endpoints write to `audit_log` (SEC-2).

---

## 6. Cross-Cutting Concerns

- **Security:** JWT auth, RBAC middleware scoping by agency+role, TLS everywhere,
  encrypted-at-rest DB, secrets in vault/env (never in repo).
- **Explainability:** enforced at the `Recommendation` type level — no output ships
  without `evidence[]` + `rationale`. UI renders "why" on every card.
- **Observability:** structured logs, request tracing, agent decision traces,
  metrics (latency, acceptance rate, source uptime) → dashboard.
- **Resilience:** each source normalizer + agent isolated; circuit breakers; stale
  data flagged with age; degrade confidence rather than fail.
- **Cost control:** cache LLM/imagery calls; tiered triggering (urgent = immediate,
  routine = batched); confidence-gated re-runs.

---

## 7. Testing Strategy

| Level | What |
|---|---|
| Unit | each normalizer (schema conformance), each agent's scoring/logic |
| Contract | agent I/O contract — every output has evidence + confidence |
| Integration | ingest → orchestrator → agent → recommendation E2E on synthetic incident |
| Scenario | replay recorded disaster datasets; assert prioritization sanity |
| Load | 10k sensor stream, 100 concurrent operators |
| Security | RBAC enforcement, audit completeness, authz on every endpoint |

**Minimum viable check per component:** one runnable assert-based self-test that
fails if the core logic breaks (e.g., agent returns recommendation without evidence).

---

## 8. Deployment

- **MVP:** Docker Compose — Postgres/PostGIS, Redis, FastAPI, Next.js, OSRM.
- **Scale:** Kubernetes; Kafka replaces Redis Streams; horizontal agent workers;
  managed Postgres; CDN for map tiles.
- **CI/CD:** lint + test + build on PR; deploy previews for dashboard.
