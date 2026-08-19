"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useAuth } from "./auth-context";
import {
  API_BASE,
  fetchCitizenReports,
  fetchIncidentState,
  fetchResources,
  fetchSeverityGeojson,
} from "./api";
import type {
  CitizenReport,
  IncidentState,
  Recommendation,
  ResourcesResponse,
  WsAlertsMessage,
} from "./types";

// Shared live-data layer (plan Phase M): every console route needs the same
// WS feed / resources / incident state / citizen reports, previously all
// local to Dashboard.tsx. Extracted once so new routes are thin consumers
// instead of each re-implementing the WS connection and polling.
interface OperationsDataValue {
  resources: ResourcesResponse | null;
  recommendations: Recommendation[];
  severityGeojson: GeoJSON.FeatureCollection | null;
  incidentState: IncidentState | null;
  citizenReports: CitizenReport[];
  wsStatus: string;
  ingestRecommendations: (recs: Recommendation[]) => void;
  onIngested: (incidentId: string, recs: Recommendation[]) => void;
}

const OperationsDataContext = createContext<OperationsDataValue | null>(null);

export function OperationsDataProvider({ children }: { children: ReactNode }) {
  const { token, user } = useAuth();
  const [resources, setResources] = useState<ResourcesResponse | null>(null);
  const [recsById, setRecsById] = useState<Map<string, Recommendation>>(new Map());
  const [severityGeojson, setSeverityGeojson] = useState<GeoJSON.FeatureCollection | null>(null);
  const [incidentState, setIncidentState] = useState<IncidentState | null>(null);
  const [citizenReports, setCitizenReports] = useState<CitizenReport[]>([]);
  const [wsStatus, setWsStatus] = useState("connecting…");
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

  const onIngested = useCallback(
    (incidentId: string, recs: Recommendation[]) => {
      ingestRecommendations(recs);
      currentIncidentRef.current = incidentId;
      refreshSeverity(incidentId);
      refreshIncidentState(incidentId);
      refreshCitizenReports();
    },
    [ingestRecommendations, refreshSeverity, refreshIncidentState, refreshCitizenReports]
  );

  const value: OperationsDataValue = {
    resources,
    recommendations: [...recsById.values()],
    severityGeojson,
    incidentState,
    citizenReports,
    wsStatus,
    ingestRecommendations,
    onIngested,
  };

  return (
    <OperationsDataContext.Provider value={value}>{children}</OperationsDataContext.Provider>
  );
}

export function useOperationsData(): OperationsDataValue {
  const ctx = useContext(OperationsDataContext);
  if (!ctx) throw new Error("useOperationsData must be used within OperationsDataProvider");
  return ctx;
}
