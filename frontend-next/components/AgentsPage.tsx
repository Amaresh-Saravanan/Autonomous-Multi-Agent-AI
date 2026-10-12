"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { useOperationsData } from "@/lib/operations-context";
import { fetchAgentHealth, fetchMetrics } from "@/lib/api";
import { agentEntries } from "@/lib/incident-format";
import type { AgentHealth, MetricsSummary } from "@/lib/types";

const AGENT_NAMES: Record<string, string> = {
  "AG-1": "Disaster Assessment",
  "AG-2": "Damage Assessment",
  "AG-3": "Rescue Planning",
  "AG-4": "Medical Coordination",
  "AG-5": "Resource Allocation",
  "AG-6": "Route Optimization",
  "AG-7": "Citizen Assistance",
  "AG-8": "Situational Intelligence",
};
const ALL_AGENTS = Object.keys(AGENT_NAMES);

// AI system status (tracker 3.11.6.9, UX_DESIGN §3.3 Agents): AG-1..8 cards
// with latest output for the currently-live incident (operations-context's
// incidentState, not a new fetch) + coarse per-route latency (GET /metrics).
// [needs-backend: agent health] — the orchestrator is a fixed StateGraph
// with no per-agent health/timing export; "degraded/error state" from the
// UX spec isn't derivable from anything that exists, so it's omitted rather
// than faked. Last-run is approximated from each rec's created_at.
export default function AgentsPage() {
  const { token } = useAuth();
  const { incidentState } = useOperationsData();
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [health, setHealth] = useState<Map<string, AgentHealth>>(new Map());

  useEffect(() => {
    // Metrics are operator+; viewers still get per-agent health.
    if (user?.role !== "viewer") fetchMetrics(token).then(setMetrics).catch(console.error);
    fetchAgentHealth(token)
      .then((rows) => setHealth(new Map(rows.map((h) => [h.agent_id, h]))))
      .catch(console.error);
  }, [token, user?.role]);

  const outputs = new Map(agentEntries(incidentState));
  // Aggregate every /api/v1/ingestion/* route into one orchestration-intake figure.
  const ingestRoutes = Object.entries(metrics?.routes ?? {}).filter(([path]) =>
    path.startsWith("/api/v1/ingestion/")
  );
  const ingestCount = ingestRoutes.reduce((n, [, r]) => n + r.count, 0);
  const ingestLatency = ingestCount
    ? {
        count: ingestCount,
        avg_latency_ms: ingestRoutes.reduce((n, [, r]) => n + r.avg_latency_ms * r.count, 0) / ingestCount,
        p95_latency_ms: Math.max(...ingestRoutes.map(([, r]) => r.p95_latency_ms)),
      }
    : undefined;

  return (
    <div className="h-full overflow-y-auto p-console-lg">
      <h1 className="mb-console-md font-console-display-header text-console-display-header uppercase tracking-wider text-console-on-surface">
        Agents
      </h1>
      {ingestLatency && (
        <div className="mb-console-lg font-console-data-tabular text-console-data-tabular text-console-on-surface-variant">
          Ingestion latency: avg {ingestLatency.avg_latency_ms.toFixed(0)}ms · p95{" "}
          {ingestLatency.p95_latency_ms.toFixed(0)}ms ({ingestLatency.count} runs)
        </div>
      )}

      <div className="grid grid-cols-1 gap-console-md md:grid-cols-2 lg:grid-cols-4">
        {ALL_AGENTS.map((agentId) => {
          const rec = outputs.get(agentId);
          const h = health.get(agentId);
          // DEGRADED = ran on its rule-based fallback (e.g. no LLM key);
          // "degraded" is reserved for repeated real failures.
          const fallback = h?.status === "DEGRADED";
          const statusLabel = h?.degraded_mode && !fallback ? "degraded" : fallback ? "rule-based" : rec || h ? "active" : "idle";
          return (
            <div
              key={agentId}
              className="rounded-xl border border-console-outline-variant/40 bg-console-surface/80 p-console-md shadow-lg backdrop-blur-xl"
            >
              <div className="flex items-center justify-between">
                <span className="font-console-data-tabular text-console-data-tabular font-semibold text-console-primary">
                  {agentId}
                </span>
                <span
                  className={`font-console-label-caps text-[9px] font-bold uppercase ${
                    h?.degraded_mode && !fallback
                      ? "text-[var(--sev-high)]"
                      : rec || h
                        ? "text-[var(--sev-low)]"
                        : "text-console-outline"
                  }`}
                >
                  {statusLabel}
                </span>
              </div>
              <div className="mt-1 font-console-body-sm text-console-body-sm text-console-on-surface-variant">
                {AGENT_NAMES[agentId]}
              </div>
              {rec ? (
                <>
                  <p className="mt-2 font-console-body-sm text-[11px] text-console-on-surface-variant">
                    {rec.rationale}
                  </p>
                  <p className="mt-2 font-console-data-tabular text-[10px] text-console-outline">
                    confidence {rec.confidence.toFixed(2)}
                    {h?.last_run ? ` · last run ${h.last_run}` : ""}
                  </p>
                  {h?.last_error && !fallback && (
                    <p className="mt-1 font-console-data-tabular text-[10px] text-[var(--sev-high)]">
                      {h.failure_count} failures · {h.last_error}
                    </p>
                  )}
                </>
              ) : (
                <p className="mt-2 font-console-body-sm text-[11px] text-console-outline">
                  No output for the current incident.
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
