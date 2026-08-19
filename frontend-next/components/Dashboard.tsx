"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  API_BASE,
  fetchCitizenReports,
  fetchIncidentState,
  fetchResources,
  fetchSeverityGeojson,
} from "@/lib/api";
import type {
  CitizenReport,
  IncidentState,
  Recommendation,
  ResourcesResponse,
  WsAlertsMessage,
} from "@/lib/types";
import LoginOverlay from "./LoginOverlay";
import BrandBar from "./BrandBar";
import WhoAmI from "./WhoAmI";
import MapView from "./MapView";
import LayersToggle, { type LayersVisible } from "./LayersToggle";
import DashboardGrid, { type TileDef } from "./DashboardGrid";
import AlertsPanel from "./AlertsPanel";
import RecommendationsPanel from "./RecommendationsPanel";
import SituationPanel from "./SituationPanel";
import ResourcesPanel from "./ResourcesPanel";
import CitizenInboxPanel from "./CitizenInboxPanel";
import IngestForm from "./IngestForm";

export default function Dashboard() {
  const { token, user } = useAuth();
  const [resources, setResources] = useState<ResourcesResponse | null>(null);
  const [recsById, setRecsById] = useState<Map<string, Recommendation>>(new Map());
  const [severityGeojson, setSeverityGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [incidentState, setIncidentState] = useState<IncidentState | null>(null);
  const [citizenReports, setCitizenReports] = useState<CitizenReport[]>([]);
  const [wsStatus, setWsStatus] = useState("connecting…");
  const [layersVisible, setLayersVisible] = useState<LayersVisible>({
    severity: true,
    routes: true,
    resources: true,
  });
  const [editMode, setEditMode] = useState(false);
  const currentIncidentRef = useRef<string | null>(null);

  const ingestRecommendations = useCallback((recs: Recommendation[]) => {
    setRecsById((prev) => {
      const next = new Map(prev);
      recs.forEach((rec) => next.set(rec.rec_id, rec));
      return next;
    });
  }, []);

  const refreshSeverity = useCallback(
    async (incidentId: string) => {
      const geojson = await fetchSeverityGeojson(token, incidentId);
      setSeverityGeojson(geojson);
    },
    [token]
  );

  const refreshIncidentState = useCallback(
    async (incidentId: string) => {
      const state = await fetchIncidentState(token, incidentId);
      setIncidentState(state);
    },
    [token]
  );

  // Citizen reports don't wake any agent (tracker 3.3 design) so there's no
  // WS push for them -- poll instead of relying on the alerts socket.
  const refreshCitizenReports = useCallback(async () => {
    const reports = await fetchCitizenReports(token, currentIncidentRef.current ?? undefined);
    setCitizenReports(reports);
  }, [token]);

  // Load resources + open the WS feed once authenticated (mirrors the
  // onAuthenticated() flow from the original Phase 0 shell, since retired).
  useEffect(() => {
    if (!user) return;
    fetchResources(token).then(setResources).catch(console.error);
    refreshCitizenReports().catch(console.error);
    const citizenPoll = setInterval(() => {
      refreshCitizenReports().catch(console.error);
    }, 5000);

    let ws: WebSocket;
    let closedByUs = false;
    function connect() {
      ws = new WebSocket(API_BASE.replace("http", "ws") + "/ws/alerts");
      ws.onopen = () => setWsStatus("live");
      ws.onclose = () => {
        setWsStatus("reconnecting…");
        if (!closedByUs) setTimeout(connect, 2000);
      };
      ws.onmessage = (evt) => {
        const msg: WsAlertsMessage = JSON.parse(evt.data);
        ingestRecommendations(msg.recommendations);
        currentIncidentRef.current = msg.incident_id;
        refreshSeverity(msg.incident_id);
        refreshIncidentState(msg.incident_id);
        refreshCitizenReports();
      };
    }
    connect();
    return () => {
      closedByUs = true;
      ws?.close();
      clearInterval(citizenPoll);
    };
  }, [
    user,
    token,
    ingestRecommendations,
    refreshSeverity,
    refreshIncidentState,
    refreshCitizenReports,
  ]);

  if (!user) return <LoginOverlay />;

  const recommendations = [...recsById.values()];
  const criticalPending = recommendations.filter(
    (r) => r.severity >= 0.85 && r.status === "pending"
  ).length;
  const highPending = recommendations.filter(
    (r) => r.severity >= 0.5 && r.severity < 0.85 && r.status === "pending"
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
    <div className="relative h-screen w-screen overflow-hidden">
      <BrandBar criticalCount={criticalPending} highCount={highPending} />
      <WhoAmI editMode={editMode} onToggleEdit={() => setEditMode((v) => !v)} />
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
      <IngestForm
        onIngested={(incidentId, recs) => {
          ingestRecommendations(recs);
          currentIncidentRef.current = incidentId;
          refreshSeverity(incidentId);
          refreshIncidentState(incidentId);
          refreshCitizenReports();
        }}
      />
    </div>
  );
}
