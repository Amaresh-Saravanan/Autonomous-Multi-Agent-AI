"use client";

import { useState } from "react";
import { useOperationsData } from "@/lib/operations-context";
import MapView from "./MapView";
import type { LayersVisible } from "./LayersToggle";

// Route planning (tracker 3.11.6.6, UX_DESIGN §3.3 Routes) — large map (MapView
// already derives route lines from AG-6 recommendations' details.route_line/
// blocked, reused as-is) + a side list of AG-6 recs with derived status.
// [needs-backend: route-status entity] — "degraded" status and operator
// dispatch mutation (in-transit/arrived) have no backing model; only
// open/blocked is derivable from details.blocked today (tracker BE-4).
export default function RoutesPage() {
  const { resources, recommendations, severityGeojson } = useOperationsData();
  const [layersVisible] = useState<LayersVisible>({ severity: false, routes: true, resources: true });

  const routeRecs = recommendations.filter((r) => r.agent_id === "AG-6" && r.details?.route_line);

  return (
    <div className="relative h-full w-full overflow-hidden">
      <MapView
        resources={resources}
        recommendations={recommendations}
        severityGeojson={severityGeojson}
        layersVisible={layersVisible}
      />

      <div className="absolute top-md right-md bottom-md z-20 flex w-80 max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-xl border border-console-outline-variant/40 bg-console-surface/85 shadow-lg backdrop-blur-xl">
        <div className="border-b border-console-outline-variant/20 bg-console-surface-container-low/50 px-md py-sm">
          <h3 className="font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
            Routes ({routeRecs.length})
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto p-sm">
          {routeRecs.map((r) => {
            const blocked = !!r.details?.blocked;
            return (
              <div
                key={r.rec_id}
                className="mb-sm rounded-md border border-console-outline-variant/20 bg-console-surface-container/60 px-sm py-sm"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-console-data-tabular text-console-data-tabular text-console-on-surface">
                    {r.incident_id}
                  </span>
                  <span
                    className={`font-console-label-caps text-[9px] font-bold uppercase ${
                      blocked ? "text-[var(--sev-critical)]" : "text-[var(--sev-low)]"
                    }`}
                  >
                    {blocked ? "⊘ blocked" : "✓ open"}
                  </span>
                </div>
                <p className="mt-1 font-console-body-sm text-[11px] text-console-on-surface-variant">
                  {r.rationale}
                </p>
              </div>
            );
          })}
          {routeRecs.length === 0 && (
            <div className="p-sm font-console-body-sm text-console-body-sm text-console-on-surface-variant">
              No active routes.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
