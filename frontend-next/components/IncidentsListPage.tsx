"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { fetchIncidents } from "@/lib/api";
import { relativeAge } from "@/lib/incident-format";
import type { IncidentSummary } from "@/lib/types";

// Incident list (tracker 3.11.6.2, UX_DESIGN §3.3 Incidents) — severity,
// location, status, age, last update, assigned agencies. Severity/agency
// aren't in GET /incidents' shape (BE-1 doesn't compute them — they live
// per-agent in each incident's blackboard state, not the registry), so this
// shows what the registry actually has: location, event count, last
// activity. Clicking a row opens /incidents/[id] for the full picture.
export default function IncidentsListPage() {
  const { token } = useAuth();
  const router = useRouter();
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);

  const refresh = useCallback(() => {
    fetchIncidents(token).then(setIncidents).catch(console.error);
  }, [token]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  return (
    <div className="h-full overflow-y-auto p-lg">
      <h1 className="mb-md font-console-display-header text-console-display-header uppercase tracking-wider text-console-on-surface">
        Incidents ({incidents.length})
      </h1>
      <div className="overflow-hidden rounded-xl border border-console-outline-variant/40 bg-console-surface/80 shadow-lg backdrop-blur-xl">
        <table className="w-full">
          <thead>
            <tr className="border-b border-console-outline-variant/20 bg-console-surface-container-low/50">
              <th className="px-md py-sm text-left font-console-label-caps text-console-label-caps uppercase text-console-on-surface-variant">
                Incident
              </th>
              <th className="px-md py-sm text-left font-console-label-caps text-console-label-caps uppercase text-console-on-surface-variant">
                Location
              </th>
              <th className="px-md py-sm text-left font-console-label-caps text-console-label-caps uppercase text-console-on-surface-variant">
                Events
              </th>
              <th className="px-md py-sm text-left font-console-label-caps text-console-label-caps uppercase text-console-on-surface-variant">
                Last activity
              </th>
            </tr>
          </thead>
          <tbody>
            {incidents.map((inc) => (
              <tr
                key={inc.incident_id}
                onClick={() => router.push(`/incidents/${inc.incident_id}`)}
                className="cursor-pointer border-b border-console-outline-variant/10 last:border-0 hover:bg-console-surface-container/40"
              >
                <td className="px-md py-sm font-console-data-tabular text-console-data-tabular text-console-on-surface">
                  {inc.incident_id}
                </td>
                <td className="px-md py-sm font-console-body-compact text-console-body-compact text-console-on-surface-variant">
                  {inc.district || inc.state || "unresolved"}
                </td>
                <td className="px-md py-sm font-console-data-tabular text-console-data-tabular text-console-on-surface-variant">
                  {inc.count}
                </td>
                <td className="px-md py-sm font-console-data-tabular text-console-data-tabular text-console-on-surface-variant">
                  {relativeAge(inc.last_ts)}
                </td>
              </tr>
            ))}
            {incidents.length === 0 && (
              <tr>
                <td colSpan={4} className="px-md py-lg text-center font-console-body-sm text-console-body-sm text-console-on-surface-variant">
                  No incidents yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
