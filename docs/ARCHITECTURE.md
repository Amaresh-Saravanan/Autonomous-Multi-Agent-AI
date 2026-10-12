# Architecture

Status: describes the current `backend/` (reference). `backend-v2/` will converge on
the same shape; update this file as v2 diverges.

## Flow
Sources (IoT, satellite, weather, citizen) -> `POST /ingest/{source_type}` ->
normalizers (common `Event`) -> incident clustering -> orchestrator (LangGraph
`StateGraph`, fixed order AG-1..AG-6, AG-8, trigger-filtered) <-> blackboard ->
recommendations / severity grid / alerts / audit log -> Next.js console over REST + `/ws/alerts`.

## Invariants
- Agents only recommend. Every `Recommendation` carries non-empty `evidence` and `rationale`.
- Humans approve/reject via `POST /recommendations/{id}/approve|reject`; audited; the blackboard is overwritten only if the recommendation is still the agent's latest.
- Every agent has a rule-based path; the LLM (Groq) is optional.
- AG-7 (citizen chat) is request/response at `POST /citizen/chat`, outside the orchestrator.
- RBAC: JWT roles viewer < operator < admin on all REST except `/ingest`, `/citizen/chat`, `/health`.

## State
Blackboard: in-memory, Redis if `REDIS_URL` is reachable. Recommendations, audit and
metrics are in-memory (reset on restart) - the main blocker for horizontal scaling.

See `PRD.md` (requirements), `TDD.md` (design), `MIGRATION_TRACKER.md` (status).
