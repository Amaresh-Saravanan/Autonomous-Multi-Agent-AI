"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { API_BASE, fetchResources, fetchSeverityGeojson } from "@/lib/api";
import type { Recommendation, ResourcesResponse, WsAlertsMessage } from "@/lib/types";
import LoginOverlay from "./LoginOverlay";
import BrandBar from "./BrandBar";
import WhoAmI from "./WhoAmI";
import MapView from "./MapView";
import LayersToggle, { type LayersVisible } from "./LayersToggle";
import DashboardGrid, { type TileDef } from "./DashboardGrid";
import AlertsPanel from "./AlertsPanel";
import RecommendationsPanel from "./RecommendationsPanel";
import IngestForm from "./IngestForm";

export default function Dashboard() {
  const { token, user } = useAuth();
  const [resources, setResources] = useState<ResourcesResponse | null>(null);
  const [recsById, setRecsById] = useState<Map<string, Recommendation>>(new Map());
  const [severityGeojson, setSeverityGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
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

  // Load resources + open the WS feed once authenticated (mirrors the
  // legacy onAuthenticated() flow from frontend/index.html).
  useEffect(() => {
    if (!user) return;
    fetchResources(token).then(setResources).catch(console.error);

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
      };
    }
    connect();
    return () => {
      closedByUs = true;
      ws?.close();
    };
  }, [user, token, ingestRecommendations, refreshSeverity]);

  if (!user) return <LoginOverlay />;

  const recommendations = [...recsById.values()];

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
  ];

  return (
    <div className="relative h-screen w-screen overflow-hidden">
      <BrandBar />
      <WhoAmI editMode={editMode} onToggleEdit={() => setEditMode((v) => !v)} />
      <MapView
        resources={resources}
        recommendations={recommendations}
        severityGeojson={severityGeojson}
        layersVisible={layersVisible}
      />
      <DashboardGrid tiles={tiles} editMode={editMode} />
      <IngestForm
        onIngested={(incidentId, recs) => {
          ingestRecommendations(recs);
          currentIncidentRef.current = incidentId;
          refreshSeverity(incidentId);
        }}
      />
    </div>
  );
}
