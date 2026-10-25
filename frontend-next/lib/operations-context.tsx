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
  fetchRecommendations,
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
  onIngested: (incidentId: string) => void;
}

const OperationsDataContext = createContext<OperationsDataValue | null>(null);

export function OperationsDataProvider({ children }: { children: ReactNode }) {
  const { token, user, logout } = useAuth();
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

  // V2's alert payload carries only {incident_id, level, message} — the
  // recommendations themselves aren't inlined (see
  // docs/archive/BACKEND_V2_FRONTEND_COMPATIBILITY.md), so an alert triggers a
  // re-fetch instead of a direct merge.
  const refreshRecommendations = useCallback(async () => {
    const recs = await fetchRecommendations(token);
    ingestRecommendations(recs);
  }, [token, ingestRecommendations]);

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
    if (!user || !token) return;
    const activeToken = token; // narrow once; nested closures below don't retain the guard above
    fetchResources(token).then(setResources).catch(console.error);
    // Load recommendations already pending before this page loaded — the WS
    // below only pushes *new* ones, so without this a mid-incident refresh
    // shows an empty panel until the next live event arrives.
    fetchRecommendations(token).then(ingestRecommendations).catch(console.error);
    refreshCitizenReports().catch(console.error);
    const citizenPoll = setInterval(() => {
      refreshCitizenReports().catch(console.error);
    }, 15000);

    let ws: WebSocket;
    let closedByUs = false;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    function connect() {
      // V2: /ws/alerts requires the same JWT issued at login — the browser
      // can't set a custom Authorization header on a WS handshake, so the
      // token travels as a query param instead.
      ws = new WebSocket(
        `${API_BASE.replace(/^http/, "ws")}/ws/alerts?token=${encodeURIComponent(activeToken)}`
      );
      ws.onopen = () => setWsStatus("live");
      ws.onclose = (evt) => {
        if (closedByUs) return;
        // 4401 = the backend rejected our token (expired/revoked): sign out
        // instead of reconnecting forever with a dead credential.
        if (evt.code === 4401) {
          logout();
          return;
        }
        setWsStatus("reconnecting…");
        retryTimer = setTimeout(connect, 2000);
      };
      ws.onmessage = (evt) => {
        let msg: WsAlertsMessage;
        try {
          msg = JSON.parse(evt.data);
        } catch {
          return; // ignore malformed frames rather than killing the socket handler
        }
        currentIncidentRef.current = msg.incident_id;
        // One failing refresh must not block the others.
        void Promise.allSettled([
          refreshRecommendations(),
          refreshSeverity(msg.incident_id),
          refreshIncidentState(msg.incident_id),
          refreshCitizenReports(),
        ]);
      };
    }
    connect();
    return () => {
      closedByUs = true;
      clearTimeout(retryTimer);
      ws?.close();
      clearInterval(citizenPoll);
    };
  }, [
    user,
    token,
    logout,
    refreshRecommendations,
    refreshSeverity,
    refreshIncidentState,
    refreshCitizenReports,
  ]);

  const onIngested = useCallback(
    (incidentId: string) => {
      // No recommendations yet — the agent chain hasn't run. Setting the
      // current incident now means the WS alert that arrives once it does
      // finish refreshes the right incident's severity/state immediately.
      currentIncidentRef.current = incidentId;
      refreshSeverity(incidentId);
      refreshIncidentState(incidentId);
      refreshCitizenReports();
    },
    [refreshSeverity, refreshIncidentState, refreshCitizenReports]
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
