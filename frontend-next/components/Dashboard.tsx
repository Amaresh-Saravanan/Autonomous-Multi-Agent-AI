"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { useOperationsData } from "@/lib/operations-context";
import type { Recommendation } from "@/lib/types";
import MapView from "./MapView";
import LayersToggle, { type LayersVisible } from "./LayersToggle";
import DashboardGrid, { type TileDef } from "./DashboardGrid";
import AlertsPanel from "./AlertsPanel";
import RecommendationsPanel from "./RecommendationsPanel";
import SituationPanel from "./SituationPanel";
import ResourcesPanel from "./ResourcesPanel";
import CitizenInboxPanel from "./CitizenInboxPanel";
import IngestForm from "./IngestForm";

// /command body (plan Phase M carries this over unchanged; trimming it down
// to the cockpit spec -- top-3 alerts only, etc. -- is Phase O, not this one).
// Auth guard and live-data wiring now live in the (console) shell/provider,
// not here.
export default function Dashboard() {
  const { user } = useAuth();
  const {
    resources,
    recommendations,
    severityGeojson,
    incidentState,
    citizenReports,
    wsStatus,
    ingestRecommendations,
    onIngested,
  } = useOperationsData();
  const [layersVisible, setLayersVisible] = useState<LayersVisible>({
    severity: true,
    routes: true,
    resources: true,
  });
  const [editMode, setEditMode] = useState(false);

  if (!user) return null;

  const criticalPending = recommendations.filter(
    (r) => r.severity >= 0.85 && r.status === "pending"
  ).length;

  const tiles: TileDef[] = [
    {
      key: "layers",
      title: "Layers",
      content: <LayersToggle value={layersVisible} onChange={setLayersVisible} />,
    },
    {
      key: "alerts",
      title: "Alerts",
      content: (
        <AlertsPanel
          recommendations={recommendations}
          onDecided={(r) => ingestRecommendations([r])}
        />
      ),
    },
    {
      key: "recs",
      title: "Recommendations",
      content: (
        <RecommendationsPanel
          recommendations={recommendations}
          wsStatus={wsStatus}
          onDecided={(r) => ingestRecommendations([r])}
        />
      ),
    },
    {
      key: "situation",
      title: "Situation Summary",
      content: <SituationPanel summary={incidentState?.["AG-8"] as Recommendation | undefined} />,
    },
    {
      key: "resources",
      title: "Resource Status",
      content: <ResourcesPanel resources={resources} />,
    },
    {
      key: "citizen",
      title: "Citizen Reports",
      content: <CitizenInboxPanel reports={citizenReports} />,
    },
  ];

  return (
    <div className="relative h-full w-full overflow-hidden">
      <button
        onClick={() => setEditMode((v) => !v)}
        aria-pressed={editMode}
        className={`absolute top-3 right-3 z-40 flex cursor-pointer items-center gap-2 rounded-lg border px-console-md py-console-sm font-console-label-caps text-console-label-caps backdrop-blur-md transition-colors ${
          editMode
            ? "border-console-primary bg-console-primary/20 text-console-on-surface"
            : "border-console-outline-variant/30 bg-console-surface-container/80 text-console-on-surface hover:bg-console-surface-bright/80"
        }`}
      >
        {editMode ? "Lock layout" : "Edit layout"}
      </button>
      <MapView
        resources={resources}
        recommendations={recommendations}
        severityGeojson={severityGeojson}
        layersVisible={layersVisible}
      />
      <DashboardGrid tiles={tiles} editMode={editMode} role={user.role} />
      {/* Screen readers announce new critical alerts even when the operator
          isn't looking at the panel (UX_DESIGN §6). */}
      <div className="sr-only" role="status" aria-live="assertive">
        {criticalPending > 0
          ? `${criticalPending} critical alert${criticalPending > 1 ? "s" : ""} pending`
          : ""}
      </div>
      <IngestForm onIngested={onIngested} />
    </div>
  );
}
