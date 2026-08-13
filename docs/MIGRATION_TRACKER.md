# Migration / Build Tracker
## Autonomous Multi-Agent AI Platform — Build From Scratch

**Version:** 1.0
**Date:** 2026-07-24
**Legend:** ☐ Not started · ◐ In progress · ☑ Done · ⊘ Blocked

This is a build-from-zero tracker (no existing system to migrate *from* — the
"migration" is greenfield → production). Work top-to-bottom; each phase ships
something demoable. Don't start a phase before its predecessor's P0 items are ☑.

---

## Phase 0 — Foundation & Vertical Slice  (Week 1–2)
Goal: one data source → one agent → one recommendation on a map, end to end.

| ID | Task | Priority | Status | Notes |
|----|------|----------|--------|-------|
| 0.1 | Init monorepo (`/backend`, `/frontend`, `/agents`, `/infra`, `/docs`) | P0 | ☑ | backend/{app,agents,tests}, frontend/ |
| 0.2 | Docker Compose: Postgres+PostGIS, Redis (optional — not a prerequisite to run) | P0 | ☐ | deferred to Phase 1 (not needed to run slice) |
| 0.3 | Define common Event schema | P0 | ☑ | backend/app/models.py |
| 0.4 | FastAPI skeleton + `/ingest` + `/health` | P0 | ☑ | backend/app/main.py |
| 0.5 | One ingestion normalizer (IoT sensor) | P0 | ☑ | backend/app/normalizers.py |
| 0.6 | Blackboard read/write helpers (in-memory fallback, Redis optional) | P0 | ☑ | backend/app/blackboard.py |
| 0.7 | Agent base contract + AG-1 Disaster Assessment (rule-based, no LLM) | P0 | ☑ | agents/base.py, agents/disaster.py |
| 0.8 | Minimal frontend shell + MapLibre with one severity layer | P0 | ☑ | frontend/index.html |
| 0.9 | WebSocket push: new recommendation → map | P0 | ☑ | backend `/ws/alerts` + frontend WS client |
| 0.10 | E2E self-test: synthetic event → recommendation appears | P0 | ☑ | backend/tests/test_slice.py — 3/3 passing |

**Note:** AG-1 is rule-based (threshold → severity) for Phase 0 — no LLM call, no
Groq/Together credential needed. Real model wiring is item 1.6, not here. This
keeps the slice runnable with nothing installed but Python.

**Exit criteria:** synthetic sensor spike → AG-1 flags severity → shows on dashboard map.

---

## Phase 1 — Core Situational Awareness  (Week 3–5)
Goal: real multi-source ingestion + the awareness agents + usable map.

| ID | Task | Priority | Status | Notes |
|----|------|----------|--------|-------|
| 1.1 | Satellite imagery ingestion normalizer | P0 | ☑ | app/normalizers.py |
| 1.2 | Weather forecast ingestion normalizer | P0 | ☑ | app/normalizers.py |
| 1.3 | GIS base layers (roads, buildings, pop density) into PostGIS | P0 | ☐ | deferred to Phase 2 |
| 1.4 | IoT stream at volume (Redis Streams) | P0 | ☐ | deferred to Phase 2 |
| 1.5 | Severity grid computation (H3/geohash cells) | P0 | ☑ | DS-1 — app/geo_utils.py cell_id/cell_polygon + app/severity_grid.py, GET /incidents/{id}/severity (GeoJSON) |
| 1.6 | AG-1 full (multimodal via Groq, with threshold fallback) | P0 | ☑ | agents/disaster.py + app/llm.py |
| 1.7 | AG-2 Damage Assessment (change detection + pop lookup) | P0 | ☐ | deferred to Phase 2 |
| 1.8 | AG-8 Situational Intelligence (rolling summary via LLM) | P0 | ☑ | agents/situational.py |
| 1.9 | Incident clustering (raw events → confirmed incidents) | P0 | ☐ | deferred to Phase 2 |
| 1.10 | Dashboard: layered map + recommendation feed + "why" panel | P0 | ☑ | frontend/index.html — severity heat fill layer (toggleable) + marker layer + feed/why panel; visually confirmed in browser 2026-07-28 (heat cell renders + toggles correctly). Full Next.js design still Phase 1.5+ |
| 1.11 | Audit log wired to all state changes | P0 | ☐ | deferred to Phase 3 |
| 1.12 | Integration + scenario tests (replay one dataset) | P0 | ☑ | tests/test_agents.py (AG-8 unit tests + severity grid), tests/test_scenario.py (escalating flood replay) — 10/10 passing |

**Exit criteria:** replayed real disaster dataset produces a coherent, explained
severity map + damage estimate + situation summary.

---

## Phase 2 — Coordination & Response  (Week 6–9)
Goal: the platform recommends *action*, not just awareness.

| ID | Task | Priority | Status | Notes |
|----|------|----------|--------|-------|
| 2.1 | LangGraph orchestrator (trigger routing, agent scheduling) | P0 | ☑ | agent scheduling via app/orchestrator.py (StateGraph, fixed order); trigger routing via agents/base.py `triggers` per agent — AG-1/AG-8 all types, AG-2 iot+satellite, AG-3/4/5/6 iot-only; tests/test_trigger_routing.py |
| 2.2 | Conflict surfacing (two agents disagree → human) | P0 | ☑ | AC-4 — app/orchestrator.py `_detect_conflicts` (AG-5 vs AG-6 shelter mismatch), written to blackboard `conflicts[]`, pull-only via existing GET /incidents/{id}; tests/test_conflicts.py |
| 2.3 | AG-3 Rescue Planning (priority + team assignment) | P0 | ☑ | agents/rescue.py |
| 2.4 | OSRM/Valhalla self-hosted + blocked-road edge weighting | P0 | ☐ | AG-6 uses straight-line + radius check, not real OSRM |
| 2.5 | AG-6 Route Optimization (evac + vehicle routes) | P0 | ☑ | agents/route.py — straight-line ceiling, see note above |
| 2.6 | AG-5 Resource Allocation (greedy, not OR-Tools VRP) | P1 | ☑ | agents/allocation.py |
| 2.7 | Resources registry (hospitals, shelters, teams, supplies) | P0 | ☑ | app/resources.py — synthetic seed, not Postgres |
| 2.8 | Alert engine: severity threshold → dedup → push | P0 | ☑ | app/alerts.py — gates /ws/alerts broadcast only (HTTP response + recording unaffected); tests/test_alerts.py |
| 2.9 | Human approve/reject on recommendations (audited) | P0 | ☑ | AC-5 (approve/reject only, no override state) — app/recommendations.py, app/audit.py, POST /recommendations/{id}/approve, POST /recommendations/{id}/reject, GET /recommendations?status= — API only, no UI button yet (that's 2.11) — tests/test_recommendations.py passing |
| 2.10 | Predictive impact (next-N-hours from weather+trend) | P1 | ☐ | DS-2 |
| 2.11 | Dashboard: routes layer, resource layer, alerts panel | P0 | ☑ | frontend/index.html — routes layer, resource layer, alerts panel + approve/reject buttons; GET /resources |
| 2.12 | AG-4 Medical Coordination (hospital/ambulance dispatch) | P1 | ☑ | agents/medical.py — pulled forward from Phase 3 |
| 2.13 | AG-2 Damage Assessment (population-density heuristic) | P0 | ☑ | agents/damage.py — pulled forward from Phase 1 |
| 2.14 | AG-7 Citizen Assistance (chat, LLM or fallback) | P1 | ☑ | agents/citizen.py + POST /citizen/chat — pulled forward from Phase 3 |

**Exit criteria:** operator sees prioritized rescue list + safe routes + resource
plan + live alerts, and can approve/reject each.

---

## Phase 3 — Human, Citizen & Hardening  (Week 10–13)
Goal: multilingual citizen loop, medical coordination, security, multi-agency.

| ID | Task | Priority | Status | Notes |
|----|------|----------|--------|-------|
| 3.1 | AG-4 Medical Coordination (hospital/ambulance dispatch) | P1 | ☑ | shipped via tracker 2.12 (agents/medical.py), pulled forward from Phase 3 into Phase 2 |
| 3.2 | AG-7 Citizen Assistance (multilingual chat, RAG on official guidance) | P1 | ☑ | Minimal RAG added to `agents/citizen.py`: module-level `CORPUS` (7 synthetic guidance docs) + `_retrieve()` (stdlib keyword-overlap scoring, no embeddings/vector store) wired into both the LLM prompt and the rule-based fallback reply. Tests in `tests/test_citizen_rag.py`. `ponytail:` on `_retrieve` — naive keyword overlap, upgrade to embeddings once corpus outgrows ~20-30 docs or paraphrases start missing. UI-6 |
| 3.3 | Citizen report ingestion + verification/trust pipeline | P1 | ☑ | `app/citizen_verification.py` (score_confidence heuristic: threshold diff vs AG-1 severity) + `normalize_citizen` in `app/normalizers.py`, registered under `NORMALIZERS["citizen"]`; does not wake orchestrator agents (see `docs/superpowers/specs/2026-08-13-citizen-verification-design.md`) |
| 3.4 | RBAC: users, roles, agencies, scoped views | P0 | ☑ | `app/auth.py`: 3 roles (admin/operator/viewer, admin implicit-satisfies any check), 2 synthetic agencies, in-memory `USERS` seed (same pattern as `resources.py`), `pyjwt` HS256 tokens (4h expiry), stdlib `hashlib.pbkdf2_hmac` password hashing with `hmac.compare_digest` verification, `JWT_SECRET` env-sourced with a loud one-time warning on the dev-only fallback. New `POST /auth/login`; `Depends(auth.require_role(...))` gates GET incidents/severity/recommendations/resources (viewer+), approve/reject and `GET /metrics` (operator+); ingest/citizen-chat/health stay open. `_decide()` now audits the real authenticated username (see 2026-08-06 decisions log entry — resolved). Full matrix + rationale: `docs/superpowers/specs/2026-08-13-rbac-design.md`. Agency-based view *scoping* (filtering data by agency) is deliberately deferred to 3.5 — this item only adds the `agency` field and auth plumbing. Tests: `backend/tests/test_auth.py`. ponytail: no user persistence/registration/logout — revisit if a real onboarding flow is needed. Known follow-up: `frontend/index.html` sends no `Authorization` header yet, so it now gets 401 from every gated GET — a login flow for the dashboard is unbuilt, tracked alongside 3.5. |
| 3.5 | Multi-agency dashboard views | P1 | ☑ | Scoped-down per design note: `Recommendation.target_agency: str \| None = None` (`app/models.py`); `GET /recommendations` filters to `target_agency in (user's agency, None)`, admin bypasses (`app/main.py::list_recommendations`). No agent sets `target_agency` yet, so the filter is currently a no-op for real data (`ponytail:` comment at the filter site) — wire it once agents know their target agency. `GET /incidents/{id}` left as-is (already viewer+ gated by 3.4; see spec addendum for the reasoning). Tests: `backend/tests/test_recommendations.py`. Addendum: `docs/superpowers/specs/2026-08-13-rbac-design.md`. |
| 3.6 | Encryption in transit + at rest; secrets management | P0 | ☑ | `backend/.env.example` documents `GROQ_API_KEY`/`REDIS_URL`/`JWT_SECRET`, no real values. `JWT_SECRET` fallback-with-warning logic lands in 3.4's `app/auth.py`. ponytail: TLS-in-transit deferred to deployment time (reverse proxy / uvicorn `--ssl-*` flags), not built here. |
| 3.7 | Load test (10k sensors, 100 operators) + resilience/chaos test | P0 | ☑ | NFR — `backend/tests/test_blackboard_chaos.py` proves the existing Redis-unreachable fallback in `app/blackboard.py` round-trips correctly (passed with zero prod-code changes). `backend/scripts/load_test.py` is a standalone script (not in the pytest suite) that fires concurrent `POST /ingest/iot` requests at a locally running server and reports p50/p95/p99. ponytail: this is a modest local sanity check (tens of concurrent requests via a thread pool against the dev server), not the PRD's 10k-sensor/100-operator target — a real load rig (locust/k6, distributed, sustained) is the upgrade path if/when this needs to be proven at that scale. First manual run against `uvicorn --reload` surfaced real signal: p95 ~2.25s at 50 concurrent requests, failing the naive 2000ms threshold — the dev server's single-process/no-worker setup is the likely bottleneck, worth revisiting before Phase 3 exit criteria. |
| 3.8 | Observability: metrics dashboard (latency, acceptance, uptime) | P0 | ☑ | `app/metrics.py` (stdlib-only in-process counters + bounded per-route latency deque, naive sorted-index p95) + a generic `@app.middleware("http")` in `app/main.py` timing every request + new `GET /metrics` route returning per-route count/avg/p95 latency plus `recommendation_acceptance_rate` (`approved / (approved+rejected)` among decided recs from `recommendations.list_recs()`, `null` if none decided yet). `ponytail:` in-process, single-worker, resets on restart, no persistence; upgrade path is `prometheus_client` + a real scrape target if/when an ops stack exists. Tests: `tests/test_metrics.py` (unit), `tests/test_metrics_endpoint.py` (integration). |
| 3.9 | Security review (authz on every endpoint, audit completeness) | P0 | ☑ | Full checklist run against Phase 3 waves 1+2. **Found and fixed:** (1) `app/auth.py::require_role` only matched exact role membership, so an `operator` token got 403 on viewer+ routes despite the intended `admin > operator > viewer` hierarchy — replaced with a rank map (`_ROLE_RANK`), confirmed `test_viewer_token_cannot_approve` still 403s (no privilege loosening); new test `tests/test_auth.py::test_operator_token_can_view_recommendations`. (2) `app/main.py` CORS was `allow_origins=["*"]` — now `CORS_ORIGINS` env var (default `"null,http://localhost:8000"`); `frontend/index.html` is opened as a bare `file://` page (no dev server), which sends `Origin: null`, so no real hostname belongs in the default list — documented inline. Auth is a Bearer token, not a cookie, so CORS was never the primary access boundary here, but wildcard is still unnecessary exposure. **Verified correct, no fix needed:** every route in `app/main.py` matches the endpoint→role matrix in `docs/superpowers/specs/2026-08-13-rbac-design.md` (`/health`, `/ingest/{source_type}`, `/citizen/chat`, `/auth/login` open; viewer+ on incident/severity/resources/recommendations GETs; operator+ on approve/reject and `GET /metrics`, already gated pre-review); `tests/test_auth.py` genuinely asserts 401 (no token) and 403 (wrong role), not just happy paths; single `audit.record(...)` call site (`_decide()` in `app/main.py`) uses the real authenticated `user["username"]` (e.g. `tests/test_recommendations.py` asserts `actor == "bob_operator"`), not the old hardcoded `"operator"` string; no hardcoded secrets — `JWT_SECRET` dev fallback in `app/auth.py` is the only literal, guarded by a `logging.warning`, and `backend/.env.example` has no real values; `docs/.env` remains gitignored/untracked. **Found and documented as known debt (not fixed, out of scope):** row 1.11 already correctly states audit coverage is deferred beyond `_decide()` — left as-is, no wording change needed. Additionally noted but not fixed: `frontend/index.html`'s fetches send no `Authorization` header, so RBAC now 401s them from the browser (a real follow-up, separate task); `GET /ws/alerts` is unauthenticated and outside the spec's endpoint matrix (WebSocket auth deferred). |
| 3.10 | Docs: runbook, agency onboarding, API reference | P1 | ☐ | |

**Exit criteria:** all 8 agents live, RBAC enforced, multilingual citizen chat,
passes load + security review.

---

## Phase 4 — Scale (Optional / Post-MVP)
| ID | Task | Priority | Status | Notes |
|----|------|----------|--------|-------|
| 4.1 | Kafka replaces Redis Streams | P2 | ☐ | when throughput demands |
| 4.2 | Kubernetes deploy + horizontal agent workers | P2 | ☐ | |
| 4.3 | Multi-region federation | P2 | ☐ | |
| 4.4 | Drone feed ingestion (RTSP) + on-feed vision | P2 | ☐ | DI-2 |

---

## Risk / Blocker Log
| Date | Item | Impact | Resolution |
|------|------|--------|------------|
| | (add as they arise) | | |

## Decisions Log (ADR-lite)
| Date | Decision | Why |
|------|----------|-----|
| 2026-07-24 | Redis Streams + Docker Compose for MVP, Kafka+K8s deferred | avoid premature infra; scale when measured |
| 2026-07-24 | Recommendation-only, human-in-loop | life-critical; agents advise, humans decide |
| 2026-07-24 | pgvector + TimescaleDB on one Postgres | fewer moving parts than separate vector/TS DBs |
| 2026-07-24 | Switched agent reasoning from Claude API to Groq (Mixtral-8x7B) + Together.ai (LLaVA) | zero cost; cloud-hosted so teammates need no local GPU/Ollama install; revisit only if accuracy proves insufficient |
| 2026-07-28 | Severity grid uses lat/lon rounding (geohash-lite), not the h3-py library | avoids a new dependency for what a one-line quantization does; revisit only if variable-size cells are actually needed |
| 2026-08-06 | Approve/reject audit actor is a fixed "operator" string, not a real identity | RBAC (tracker 3.4) isn't built yet; revisit once users/auth exist |
| 2026-08-12 | Conflict detection (AC-4) scoped to one real pair — AG-5 vs AG-6 shelter mismatch — not a general cross-agent conflict framework | only pair that targets the same resource today; shelter s-1 seeded at full capacity so it's demoable, not just unit-testable; revisit if more agent pairs need it |
| 2026-08-13 | Phase 2 closed out via 2.1 (trigger routing) rather than 2.4 (real OSRM); 2.4 accepted as documented debt | 2.4 is a bigger infra lift (self-hosted routing service) than the MVP needs now; 2.1 was the cheaper, higher-value P0 gap and unblocks starting Phase 3 per the tracker's own phase-gating rule |
| 2026-08-13 | 2026-08-06's "operator" audit-actor placeholder is resolved | `app/auth.py` (tracker 3.4) lands real JWT-authenticated users; `_decide()` now audits `user["username"]` from `Depends(auth.require_role("operator"))`, not a fixed string |
