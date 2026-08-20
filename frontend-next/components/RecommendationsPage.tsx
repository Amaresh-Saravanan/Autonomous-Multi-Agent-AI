"use client";

import { useMemo, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { useOperationsData } from "@/lib/operations-context";
import RecCard from "./RecCard";
import type { Recommendation } from "@/lib/types";

type StatusTab = "pending" | "approved" | "rejected";
const TABS: StatusTab[] = ["pending", "approved", "rejected"];

// Human approval gate (tracker 3.11.6.4, UX_DESIGN §3.3 Recommendations):
// tabs by status + filters by agent/severity, full-width (vs the /command
// cockpit's trimmed panel of the same data). Reuses RecCard + the shared
// live recommendations feed operations-context already keeps current.
export default function RecommendationsPage() {
  const { recommendations, ingestRecommendations } = useOperationsData();
  const [tab, setTab] = useState<StatusTab>("pending");
  const [agentFilter, setAgentFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");

  const agentIds = useMemo(
    () => Array.from(new Set(recommendations.map((r) => r.agent_id))).sort(),
    [recommendations]
  );

  const filtered = useMemo(() => {
    return recommendations
      .filter((r) => r.status === tab)
      .filter((r) => agentFilter === "all" || r.agent_id === agentFilter)
      .filter((r) => {
        if (severityFilter === "all") return true;
        if (severityFilter === "critical") return r.severity >= 0.85;
        if (severityFilter === "high") return r.severity >= 0.5 && r.severity < 0.85;
        return r.severity < 0.5; // low
      })
      .sort((a, b) => b.created_at.localeCompare(a.created_at));
  }, [recommendations, tab, agentFilter, severityFilter]);

  function onDecided(updated: Recommendation) {
    ingestRecommendations([updated]);
  }

  return (
    <div className="h-full overflow-y-auto p-lg">
      <h1 className="mb-md font-console-display-header text-console-display-header uppercase tracking-wider text-console-on-surface">
        Recommendations
      </h1>

      <div className="mb-md flex flex-wrap items-center gap-md">
        <div className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded-md px-md py-sm font-console-label-caps text-console-label-caps uppercase transition-colors ${
                tab === t
                  ? "bg-console-primary/20 text-console-primary"
                  : "text-console-on-surface-variant hover:bg-console-surface-container/40"
              }`}
            >
              {t} ({recommendations.filter((r) => r.status === t).length})
            </button>
          ))}
        </div>

        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="rounded-md border border-console-outline-variant/40 bg-console-surface-container/60 px-sm py-sm font-console-body-sm text-console-body-sm text-console-on-surface"
        >
          <option value="all">All severities</option>
          <option value="critical">Critical</option>
          <option value="high">High</option>
          <option value="low">Low</option>
        </select>

        <select
          value={agentFilter}
          onChange={(e) => setAgentFilter(e.target.value)}
          className="rounded-md border border-console-outline-variant/40 bg-console-surface-container/60 px-sm py-sm font-console-body-sm text-console-body-sm text-console-on-surface"
        >
          <option value="all">All agents</option>
          {agentIds.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
      </div>

      <div className="max-w-2xl">
        <AnimatePresence initial={false}>
          {filtered.map((rec, i) => (
            <RecCard key={rec.rec_id} rec={rec} index={i} onDecided={onDecided} />
          ))}
        </AnimatePresence>
        {filtered.length === 0 && (
          <div className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
            No {tab} recommendations match these filters.
          </div>
        )}
      </div>
    </div>
  );
}
