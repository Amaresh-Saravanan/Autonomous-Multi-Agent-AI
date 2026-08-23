"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { fetchCitizenReports, fetchIncidentState } from "@/lib/api";
import { agentEntries } from "@/lib/incident-format";
import type { CitizenReport, IncidentState } from "@/lib/types";

// Incident command room (tracker 3.11.6.3, UX_DESIGN §3.3): header + AG-8
// summary + all agent outputs + conflicts + citizen reports for one
// incident. No embedded mini-map here (avoids a second concurrent MapLibre
// WebGL context on top of /map's) — full spatial view lives on /map, which
// this page deep-links from its own header instead.
export default function IncidentDetailPage({ incidentId }: { incidentId: string }) {
  const { token } = useAuth();
  const [state, setState] = useState<IncidentState | null>(null);
  const [reports, setReports] = useState<CitizenReport[]>([]);

  useEffect(() => {
    fetchIncidentState(token, incidentId).then(setState).catch(console.error);
    fetchCitizenReports(token, incidentId).then(setReports).catch(console.error);
  }, [token, incidentId]);

  const agents = agentEntries(state);
  const situationSummary = agents.find(([id]) => id === "AG-8")?.[1];
  const conflicts = state?.conflicts ?? [];

  return (
    <div className="h-full overflow-y-auto p-console-lg">
      <div className="mb-console-lg flex items-center justify-between">
        <div>
          <h1 className="font-console-display-header text-console-display-header uppercase tracking-wider text-console-on-surface">
            {incidentId}
          </h1>
        </div>
        <Link
          href={`/map`}
          className="rounded-md border border-console-outline-variant/30 bg-console-surface-container/80 px-console-md py-console-sm font-console-label-caps text-console-label-caps text-console-on-surface hover:bg-console-surface-bright/80"
        >
          View on map
        </Link>
      </div>

      {situationSummary && (
        <div className="mb-console-lg rounded-xl border border-console-outline-variant/40 bg-console-surface/80 p-console-md shadow-lg backdrop-blur-xl">
          <h2 className="mb-console-sm font-console-label-caps text-console-label-caps uppercase text-console-primary">
            Situation Summary (AG-8)
          </h2>
          <p className="font-console-body-sm text-console-body-sm leading-relaxed text-console-on-surface-variant">
            {situationSummary.rationale}
          </p>
        </div>
      )}

      {conflicts.length > 0 && (
        <div className="mb-console-lg rounded-xl border border-[var(--sev-critical)] bg-[var(--sev-critical)]/10 p-console-md">
          <h2 className="mb-console-sm font-console-label-caps text-console-label-caps font-bold uppercase text-[var(--sev-critical)]">
            ⚠ {conflicts.length} Conflict{conflicts.length > 1 ? "s" : ""}
          </h2>
          {conflicts.map((c, i) => (
            <div key={i} className="mb-console-sm last:mb-0">
              <p className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
                {c.rationale}
              </p>
              <p className="mt-1 font-console-data-tabular text-[10px] text-console-outline">
                {c.agents.join(" vs ")} · target {c.target}
              </p>
            </div>
          ))}
        </div>
      )}

      <h2 className="mb-console-sm font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
        Agent Outputs
      </h2>
      <div className="mb-console-lg grid grid-cols-1 gap-console-sm md:grid-cols-2 lg:grid-cols-3">
        {agents.map(([agentId, rec]) => (
          <div
            key={agentId}
            className="rounded-md border border-console-outline-variant/20 bg-console-surface-container/60 px-console-md py-console-sm"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-console-data-tabular text-console-data-tabular font-semibold text-console-on-surface">
                {agentId} · {rec.action}
              </span>
              <span className="font-console-data-tabular text-[10px] text-console-outline">
                {rec.status}
              </span>
            </div>
            <p className="mt-1 font-console-body-sm text-[11px] text-console-on-surface-variant">
              {rec.rationale}
            </p>
            <p className="mt-1 font-console-data-tabular text-[10px] text-console-outline">
              confidence {rec.confidence.toFixed(2)}
            </p>
          </div>
        ))}
        {agents.length === 0 && (
          <div className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
            No agent output yet for this incident.
          </div>
        )}
      </div>

      <h2 className="mb-console-sm font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
        Citizen Reports ({reports.length})
      </h2>
      <div className="flex flex-col gap-2">
        {reports.map((r) => (
          <div
            key={r.event_id}
            className="rounded-md border border-console-outline-variant/20 bg-console-surface-container/40 px-console-md py-console-sm"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-console-data-tabular text-console-data-tabular text-console-on-surface">
                {r.reporter_id}
              </span>
              {r.flagged_for_review && (
                <span className="font-console-label-caps text-[9px] font-bold text-[var(--sev-critical)]">
                  ⚠ FLAGGED
                </span>
              )}
            </div>
            <p className="mt-1 font-console-body-sm text-console-body-sm text-console-on-surface-variant">
              {r.message}
            </p>
          </div>
        ))}
        {reports.length === 0 && (
          <div className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
            No citizen reports for this incident.
          </div>
        )}
      </div>
    </div>
  );
}
