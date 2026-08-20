"use client";

import { useOperationsData } from "@/lib/operations-context";

// Medical dispatcher workspace (tracker 3.11.6.7, UX_DESIGN §3.3 Medical):
// hospital capacity + ambulance availability (GET /resources) and AG-4's
// casualty/dispatch output for the currently-live incident (reuses
// operations-context's incidentState — the same WS-driven state /command
// shows, not a new fetch). Cross-incident casualty roll-up across every
// known incident [needs-backend: GET /incidents (BE-1, done) + per-incident
// N+1 fetches] deferred — would mean fetching every incident's state on
// page load, not worth it against a dev-scale registry; AG-4's output for
// whichever incident is active is what a dispatcher actually watches live.
export default function MedicalPage() {
  const { resources, incidentState } = useOperationsData();
  const ag4 = incidentState?.["AG-4"];
  const casualtyRec = ag4 && "action" in ag4 ? ag4 : null;

  if (!resources) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
          Loading…
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-lg">
      <h1 className="mb-md font-console-display-header text-console-display-header uppercase tracking-wider text-console-on-surface">
        Medical
      </h1>

      {casualtyRec && (
        <div className="mb-lg rounded-xl border border-console-outline-variant/40 bg-console-surface/80 p-md shadow-lg backdrop-blur-xl">
          <h2 className="mb-sm font-console-label-caps text-console-label-caps uppercase text-console-primary">
            AG-4 Dispatch — {casualtyRec.incident_id}
          </h2>
          <div className="font-console-data-tabular text-console-data-tabular text-console-on-surface">
            {casualtyRec.action}
          </div>
          <p className="mt-1 font-console-body-sm text-console-body-sm text-console-on-surface-variant">
            {casualtyRec.rationale}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-lg lg:grid-cols-2">
        <div>
          <h2 className="mb-sm font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
            Hospital Capacity
          </h2>
          <div className="overflow-hidden rounded-xl border border-console-outline-variant/40 bg-console-surface/80 shadow-lg backdrop-blur-xl">
            <table className="w-full">
              <tbody>
                {resources.hospitals.map((h) => {
                  const cap = Number(h.capacity ?? 0);
                  const free = Number(h.free_beds ?? 0);
                  const low = cap > 0 && free / cap < 0.2;
                  return (
                    <tr key={h.id} className={`border-b border-console-outline-variant/10 last:border-0 ${low ? "bg-[var(--sev-critical)]/10" : ""}`}>
                      <td className="px-md py-sm font-console-body-compact text-console-body-compact text-console-on-surface">
                        {String(h.name ?? h.id)}
                      </td>
                      <td
                        className={`px-md py-sm text-right font-console-data-tabular text-console-data-tabular ${
                          low ? "font-bold text-[var(--sev-critical)]" : "text-console-on-surface-variant"
                        }`}
                      >
                        {low && "⚠ "}
                        {free}/{cap} free
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <h2 className="mb-sm font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
            Ambulance Fleet
          </h2>
          <div className="overflow-hidden rounded-xl border border-console-outline-variant/40 bg-console-surface/80 shadow-lg backdrop-blur-xl">
            <table className="w-full">
              <tbody>
                {resources.ambulances.map((a) => (
                  <tr key={a.id} className="border-b border-console-outline-variant/10 last:border-0">
                    <td className="px-md py-sm font-console-data-tabular text-console-data-tabular text-console-on-surface">
                      {String(a.name ?? a.id)}
                    </td>
                    <td className="px-md py-sm text-right font-console-body-compact text-console-body-compact text-console-on-surface-variant">
                      {String(a.status ?? "unknown")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {resources.supplies && (
        <div className="mt-lg rounded-xl border border-console-outline-variant/40 bg-console-surface/80 p-md shadow-lg backdrop-blur-xl">
          <h2 className="mb-sm font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
            Emergency Supplies
          </h2>
          <div className="flex gap-lg">
            {Object.entries(resources.supplies).map(([key, value]) => (
              <div key={key}>
                <div className="font-console-label-caps text-[10px] uppercase text-console-on-surface-variant">
                  {key.replace(/_/g, " ")}
                </div>
                <div className="font-console-data-tabular text-console-data-tabular text-console-on-surface">
                  {value.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
