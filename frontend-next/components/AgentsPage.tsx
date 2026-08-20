"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { useOperationsData } from "@/lib/operations-context";
import { fetchMetrics } from "@/lib/api";
import { agentEntries } from "@/lib/incident-format";
import type { MetricsSummary } from "@/lib/types";

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
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);

  useEffect(() => {
    fetchMetrics(token).then(setMetrics).catch(console.error);
  }, [token]);

  const outputs = new Map(agentEntries(incidentState));
  const ingestLatency = metrics?.routes["/ingest/{source_type}"];

  return (
    <div className="h-full overflow-y-auto p-lg">
      <h1 className="mb-md font-console-display-header text-console-display-header uppercase tracking-wider text-console-on-surface">
        Agents
      </h1>
      {ingestLatency && (
        <div className="mb-lg font-console-data-tabular text-console-data-tabular text-console-on-surface-variant">
          Orchestration latency: avg {ingestLatency.avg_latency_ms.toFixed(0)}ms · p95{" "}
          {ingestLatency.p95_latency_ms.toFixed(0)}ms ({ingestLatency.count} runs)
        </div>
      )}

      <div className="grid grid-cols-1 gap-md md:grid-cols-2 lg:grid-cols-4">
        {ALL_AGENTS.map((agentId) => {
          const rec = outputs.get(agentId);
          return (
            <div
              key={agentId}
              className="rounded-xl border border-console-outline-variant/40 bg-console-surface/80 p-md shadow-lg backdrop-blur-xl"
            >
              <div className="flex items-center justify-between">
                <span className="font-console-data-tabular text-console-data-tabular font-semibold text-console-primary">
                  {agentId}
                </span>
                <span
                  className={`font-console-label-caps text-[9px] font-bold uppercase ${
                    rec ? "text-[var(--sev-low)]" : "text-console-outline"
                  }`}
                >
                  {rec ? "active" : "idle"}
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
                    confidence {rec.confidence.toFixed(2)} · {rec.created_at}
                  </p>
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
