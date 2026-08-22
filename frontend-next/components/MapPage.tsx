"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { useOperationsData } from "@/lib/operations-context";
import { fetchIncidents, fetchIncidentState, fetchSeverityGeojson } from "@/lib/api";
import { agentEntries, relativeAge } from "@/lib/incident-format";
import type { IncidentState, IncidentSummary } from "@/lib/types";
import MapView from "./MapView";
import LayersToggle, { type LayersVisible } from "./LayersToggle";

// Dedicated operational map (tracker 3.11.5, UX_DESIGN §3.3 Map): full
// MapLibre canvas with a layer/incident rail on the left and a
// selected-incident detail sheet on the right, per spec. Reuses MapView
// (extended with an optional incidents-pin layer) and the same
// resources/severity data OperationsDataProvider already keeps live.
export default function MapPage() {
  const { token } = useAuth();
  const { resources, severityGeojson: activeSeverityGeojson } = useOperationsData();
  const [incidents, setIncidents] = useState<IncidentSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedState, setSelectedState] = useState<IncidentState | null>(null);
  const [selectedSeverity, setSelectedSeverity] = useState<GeoJSON.FeatureCollection | null>(null);
  const [layersVisible, setLayersVisible] = useState<LayersVisible>({
    severity: true,
    routes: true,
    resources: true,
  });

  const refreshIncidents = useCallback(() => {
    fetchIncidents(token).then(setIncidents).catch(console.error);
  }, [token]);

  useEffect(() => {
    refreshIncidents();
    const id = setInterval(refreshIncidents, 5000);
    return () => clearInterval(id);
  }, [refreshIncidents]);

  const selectIncident = useCallback(
    (incidentId: string) => {
      setSelectedId(incidentId);
      fetchIncidentState(token, incidentId).then(setSelectedState).catch(console.error);
      fetchSeverityGeojson(token, incidentId).then(setSelectedSeverity).catch(console.error);
    },
    [token]
  );

  const selected = incidents.find((i) => i.incident_id === selectedId) ?? null;

  return (
    <div className="relative h-full w-full overflow-hidden">
      <MapView
        resources={resources}
        recommendations={selectedId ? agentEntries(selectedState).map(([, r]) => r) : []}
        severityGeojson={selected ? selectedSeverity : activeSeverityGeojson}
        layersVisible={layersVisible}
        incidents={incidents}
        selectedIncidentId={selectedId}
        onSelectIncident={selectIncident}
      />

      {/* Left rail: layers + incident list */}
      <div className="absolute top-md left-md z-20 flex w-64 max-w-[calc(100vw-2rem)] flex-col gap-md">
        <div className="rounded-xl border border-console-outline-variant/40 bg-console-surface/85 p-md shadow-lg backdrop-blur-xl">
          <h3 className="mb-sm font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
            Layers
          </h3>
          <LayersToggle value={layersVisible} onChange={setLayersVisible} />
        </div>
        <div className="flex max-h-[60vh] flex-col overflow-hidden rounded-xl border border-console-outline-variant/40 bg-console-surface/85 shadow-lg backdrop-blur-xl">
          <div className="border-b border-console-outline-variant/20 bg-console-surface-container-low/50 px-md py-sm">
            <h3 className="font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
              Incidents ({incidents.length})
            </h3>
          </div>
          <div className="flex-1 overflow-y-auto p-sm">
            {incidents.length === 0 && (
              <div className="p-sm font-console-body-sm text-console-body-sm text-console-on-surface-variant">
                No incidents yet.
              </div>
            )}
            {incidents.map((inc) => (
              <button
                key={inc.incident_id}
                onClick={() => selectIncident(inc.incident_id)}
                className={`mb-1 flex w-full flex-col items-start gap-0.5 rounded-md px-sm py-sm text-left transition-colors ${
                  inc.incident_id === selectedId
                    ? "border-l-2 border-console-primary bg-console-primary/10"
                    : "hover:bg-console-surface-container/40"
                }`}
              >
                <span className="font-console-data-tabular text-console-data-tabular text-console-on-surface">
                  {inc.incident_id}
                </span>
                <span className="font-console-body-sm text-[11px] text-console-on-surface-variant">
                  {inc.district || inc.state || "unresolved location"} · {relativeAge(inc.last_ts)}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Right sheet: selected incident detail */}
      {selected && (
        <div className="absolute top-md right-md bottom-md z-20 flex w-80 max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-xl border border-console-outline-variant/40 bg-console-surface/85 shadow-lg backdrop-blur-xl">
          <div className="flex items-center justify-between border-b border-console-outline-variant/20 bg-console-surface-container-low/50 px-md py-sm">
            <h3 className="font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
              {selected.incident_id}
            </h3>
            <button
              onClick={() => setSelectedId(null)}
              aria-label="Close incident detail"
              className="text-console-on-surface-variant hover:text-console-on-surface"
            >
              ✕
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-md">
            <div className="mb-md font-console-body-sm text-console-body-sm text-console-on-surface-variant">
              {selected.district || "—"}{selected.state ? `, ${selected.state}` : ""} ·{" "}
              {selected.count} event{selected.count === 1 ? "" : "s"} · {relativeAge(selected.last_ts)}
            </div>

            {selectedState?.conflicts && selectedState.conflicts.length > 0 && (
              <div className="mb-md rounded-md border border-[var(--sev-critical)] bg-[var(--sev-critical)]/10 px-sm py-sm">
                <div className="font-console-label-caps text-[10px] font-bold tracking-wide text-[var(--sev-critical)]">
                  ⚠ {selectedState.conflicts.length} CONFLICT{selectedState.conflicts.length > 1 ? "S" : ""}
                </div>
                {selectedState.conflicts.map((c, i) => (
                  <p key={i} className="mt-1 font-console-body-sm text-[11px] text-console-on-surface-variant">
                    {c.rationale}
                  </p>
                ))}
              </div>
            )}

            <div className="flex flex-col gap-sm">
              {agentEntries(selectedState).map(([agentId, rec]) => (
                <div
                  key={agentId}
                  className="rounded-md border border-console-outline-variant/20 bg-console-surface-container/60 px-sm py-sm"
                >
                  <div className="font-console-data-tabular text-console-data-tabular text-console-on-surface">
                    {agentId} · {rec.action}
                  </div>
                  <p className="mt-1 font-console-body-sm text-[11px] text-console-on-surface-variant">
                    {rec.rationale}
                  </p>
                </div>
              ))}
              {agentEntries(selectedState).length === 0 && (
                <div className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
                  No agent output yet for this incident.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
