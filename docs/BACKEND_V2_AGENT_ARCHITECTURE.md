# Backend V2 Agent Architecture

## Contract (`app/agents/base.py`)

```
BaseAgent
  can_handle(context) -> bool        # triggers + (for AG-3..AG-6) severity gate
  execute(context) -> AgentResult    # the actual reasoning; may raise
  fallback(context, error) -> AgentResult   # default: FAILED, never raises
  validate_result(result) -> AgentResult    # non-empty evidence+reasoning or raise
  run(context) -> AgentResult        # template method: try execute+validate, catch into fallback
```

`AgentContext` carries `incident_id`, `source_type`, `severity`,
`location_state`/`latitude`/`longitude` (with `.location_known`),
`events`, `evidence_event_ids`, `blackboard` (other agents' current
output), `resources` (plain-dict snapshot), `llm`.

`AgentResult` statuses: `PENDING, RUNNING, SUCCESS, FAILED, TIMEOUT,
DEGRADED, SKIPPED, FALLBACK` (`app/models/agent.py::AgentStatusEnum`).

## Per-agent summary

| Agent | Triggers | What changed from V1 |
|---|---|---|
| AG-1 Disaster Assessment | iot, weather, satellite | LLM output parsed through a typed `AG1LLMOutput` schema; any LLM failure *or* malformed response falls through to the threshold path with `status=DEGRADED, fallback_used=True` and the reason in `metadata` — never reported as a successful rationale |
| AG-2 Damage Assessment | iot, satellite | Renamed `DeterministicExposureEstimator`; reasoning text explicitly says "NOT imagery change-detection" |
| AG-3 Rescue Planning | iot (+ severity ≥ 0.3) | Resources via `context.resources["teams"]`, not a direct import; `location_unavailable_result()` instead of the `[80.27, 13.08]` Chennai fallback |
| AG-4 Medical Coordination | iot (+ severity ≥ 0.3) | Same resource-injection + location-honesty pattern |
| AG-5 Resource Allocation | iot (+ severity ≥ 0.3) | `ResourceAllocator` → `AllocationStrategy` Protocol; `GreedyFallback` is the only implementation. `ORToolsOptimizer` is a named, deferred slot, not built (`ortools` isn't installed) |
| AG-6 Route Optimization | iot (+ severity ≥ 0.3) | Delegates to `services/route_service.RoutingService`; `StraightLineFallback` is explicitly labeled as not real routing. `ROUTING_PROVIDER=osrm` is a valid config value with no implementation behind it yet |
| AG-7 Citizen Assistance | on-demand, not in the chain | `Retriever`/`DocumentStore`/`VectorStore` interfaces; `KeywordRetriever` (the old 7-doc corpus) is the only implementation; explicit "information is not available" reply when nothing is retrieved and the LLM is unavailable, rather than fabricating |
| AG-8 Situational Intelligence | iot, weather, satellite (runs last) | Reads the full blackboard excluding itself; same LLM-degrades-gracefully pattern as AG-1 |

## Orchestration (Phase 16)

`orchestration/router.py` defines the fixed order (`AGENT_CHAIN`).
`orchestration/conditions.py::should_run` decides per-event whether an
agent actually executes — beyond V1's trigger check, dispatch agents
(AG-3..AG-6) are skipped below `MIN_DISPATCH_SEVERITY = 0.3`, a real
behavioral change from V1 (which ran every agent on every event
regardless of severity). `orchestration/execution.py` is the per-node
body; `orchestration/graph.py` wires it into a LangGraph `StateGraph` and
exposes `run_for_event()`, the unit of work the background queue worker
(`start_worker_thread`) calls for every dequeued ingestion job.

## Location honesty (Phase 13)

`AgentContext.location_known` is `False` whenever `location_state ==
UNKNOWN` or either coordinate is `None`. Every distance-dependent agent
(AG-3/4/5/6) checks it first and returns `location_unavailable_result()`
— `status=DEGRADED`, `action="escalate:location_unavailable"` — instead
of computing a distance against a substituted coordinate. There is no
Chennai (or any other) fallback coordinate anywhere in V2.

## Conflict detection (Phase 19)

`recommendations/conflict.py::ConflictDetector` runs a list of
`ConflictRule`s against the final blackboard snapshot after the chain
completes. `ShelterDestinationMismatch` (AG-5 vs AG-6) is the only rule
today, ported from V1's hardcoded check — but it's now a registered rule,
not a hardcoded comparison, so adding a route/medical/priority conflict
rule later is additive.
