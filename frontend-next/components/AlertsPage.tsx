"use client";

import { useMemo, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { useOperationsData } from "@/lib/operations-context";
import RecCard from "./RecCard";
import type { Recommendation } from "@/lib/types";

// Full alert triage queue (tracker 3.11.6.1, UX_DESIGN §3.3 Alerts) — not
// the /command cockpit's top-3 widget. "Alert" = pending + severity >= 0.5,
// matching AlertsPanel's existing definition (kept there for the /command
// cockpit; duplicated here as a query, not a shared component, since the
// two pages' surrounding chrome differs enough that sharing would need
// prop knobs neither call site actually wants).
export default function AlertsPage() {
  const { recommendations, ingestRecommendations } = useOperationsData();
  const [severityFilter, setSeverityFilter] = useState<"all" | "critical" | "high">("all");
  const [agentFilter, setAgentFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  const alerts = recommendations.filter((r) => r.severity >= 0.5 && r.status === "pending");
  const agentIds = useMemo(
    () => Array.from(new Set(alerts.map((r) => r.agent_id))).sort(),
    [alerts]
  );

  const filtered = useMemo(() => {
    return alerts
      .filter((r) => severityFilter === "all" || (severityFilter === "critical" ? r.severity >= 0.85 : r.severity < 0.85))
      .filter((r) => agentFilter === "all" || r.agent_id === agentFilter)
      .filter(
        (r) =>
          !search ||
          r.action.toLowerCase().includes(search.toLowerCase()) ||
          r.rationale.toLowerCase().includes(search.toLowerCase())
      )
      .sort((a, b) => b.severity - a.severity || b.created_at.localeCompare(a.created_at));
  }, [alerts, severityFilter, agentFilter, search]);

  function onDecided(updated: Recommendation) {
    ingestRecommendations([updated]);
  }

  return (
    <div className="h-full overflow-y-auto p-console-lg">
      <h1 className="mb-console-md font-console-display-header text-console-display-header uppercase tracking-wider text-console-on-surface">
        Alerts ({filtered.length})
      </h1>

      <div className="mb-console-md flex flex-wrap items-center gap-console-md">
        <div className="flex gap-1">
          {(["all", "critical", "high"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSeverityFilter(s)}
              className={`rounded-md px-console-md py-console-sm font-console-label-caps text-console-label-caps uppercase transition-colors ${
                severityFilter === s
                  ? "bg-console-primary/20 text-console-primary"
                  : "text-console-on-surface-variant hover:bg-console-surface-container/40"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <select
          value={agentFilter}
          onChange={(e) => setAgentFilter(e.target.value)}
          className="rounded-md border border-console-outline-variant/40 bg-console-surface-container/60 px-console-sm py-console-sm font-console-body-sm text-console-body-sm text-console-on-surface"
        >
          <option value="all">All agents</option>
          {agentIds.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search action or rationale…"
          className="rounded-md border border-console-outline-variant/40 bg-console-surface-container/60 px-console-sm py-console-sm font-console-body-sm text-console-body-sm text-console-on-surface placeholder:text-console-outline focus:border-console-primary focus:outline-none"
        />
      </div>

      <div className="max-w-2xl">
        <AnimatePresence initial={false}>
          {filtered.map((rec, i) => (
            <RecCard key={rec.rec_id} rec={rec} index={i} onDecided={onDecided} />
          ))}
        </AnimatePresence>
        {filtered.length === 0 && (
          <div className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
            No alerts match these filters.
          </div>
        )}
      </div>
    </div>
  );
}
