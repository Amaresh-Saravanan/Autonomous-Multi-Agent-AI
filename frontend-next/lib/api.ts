import type {
  AuditEntry,
  CitizenChatReply,
  CitizenReport,
  CurrentUser,
  IncidentState,
  IncidentSummary,
  MetricsSummary,
  Recommendation,
  ResourcesResponse,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export function decodeJwtPayload(token: string): CurrentUser {
  return JSON.parse(atob(token.split(".")[1]));
}

export async function login(
  email: string,
  password: string
): Promise<string> {
  // V2: /api/v1/auth/login, and the field is `email` (Pydantic EmailStr),
  // not `username`.
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("invalid credentials");
  const body = await res.json();
  return body.access_token as string;
}

// Wraps fetch with the bearer token; on 401 (expired/invalid) the caller
// (auth-context) drops back to the login screen.
export async function authFetch(
  url: string,
  token: string | null,
  opts: RequestInit = {}
): Promise<Response> {
  const headers = {
    ...(opts.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  return fetch(url, { ...opts, headers });
}

export async function fetchResources(
  token: string | null
): Promise<ResourcesResponse> {
  const res = await authFetch(`${API_BASE}/api/v1/resources`, token);
  if (!res.ok) throw new Error(`resources fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchRecommendations(
  token: string | null
): Promise<Recommendation[]> {
  const res = await authFetch(`${API_BASE}/api/v1/recommendations`, token);
  if (!res.ok) throw new Error(`recommendations fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchIncidents(
  token: string | null
): Promise<IncidentSummary[]> {
  const res = await authFetch(`${API_BASE}/api/v1/incidents`, token);
  if (!res.ok) throw new Error(`incidents fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchAudit(token: string | null): Promise<AuditEntry[]> {
  const res = await authFetch(`${API_BASE}/api/v1/audit`, token);
  if (!res.ok) throw new Error(`audit fetch failed: ${res.status}`);
  return res.json();
}

// DEFERRED (docs/BACKEND_V2_FRONTEND_COMPATIBILITY.md): V2 exposes
// Prometheus text format at /api/v1/health/metrics, not V1's per-route JSON
// summary. No V2 JSON-shaped metrics endpoint exists yet, so this call
// stays pointed at the old path and will 404 until that's built — flagged
// here rather than silently left broken.
export async function fetchMetrics(token: string | null): Promise<MetricsSummary> {
  const res = await authFetch(`${API_BASE}/metrics`, token);
  if (!res.ok) throw new Error(`metrics fetch failed: ${res.status}`);
  return res.json();
}

export async function postCitizenChat(
  message: string,
  language = "en"
): Promise<CitizenChatReply> {
  // V2: device-authenticated like ingestion (Phase 7 closes V1's "citizen
  // chat is open" gap). The demo UI has no device credential to send yet —
  // DEFERRED alongside the metrics gap above.
  const res = await fetch(`${API_BASE}/api/v1/citizen/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, language }),
  });
  if (!res.ok) throw new Error(`citizen chat failed: ${res.status}`);
  return res.json();
}

export async function fetchIncidentState(
  token: string | null,
  incidentId: string
): Promise<IncidentState> {
  const res = await authFetch(`${API_BASE}/api/v1/incidents/${incidentId}`, token);
  if (!res.ok) throw new Error(`incident state fetch failed: ${res.status}`);
  return res.json();
}

// DEFERRED (docs/BACKEND_V2_FRONTEND_COMPATIBILITY.md): V2 has no
// citizen_reports list endpoint or incident severity-grid endpoint yet.
// Paths left unchanged (pointing at V1 routes that don't exist on V2)
// rather than invented against a backend surface that isn't built.
export async function fetchCitizenReports(
  token: string | null,
  incidentId?: string
): Promise<CitizenReport[]> {
  const url = incidentId
    ? `${API_BASE}/citizen/reports?incident_id=${encodeURIComponent(incidentId)}`
    : `${API_BASE}/citizen/reports`;
  const res = await authFetch(url, token);
  if (!res.ok) throw new Error(`citizen reports fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchSeverityGeojson(
  token: string | null,
  incidentId: string
) {
  const res = await authFetch(
    `${API_BASE}/incidents/${incidentId}/severity`,
    token
  );
  if (!res.ok) throw new Error(`severity fetch failed: ${res.status}`);
  return res.json();
}

export async function decideRecommendation(
  token: string | null,
  recId: string,
  action: "approve" | "reject"
): Promise<Recommendation> {
  // V2: one unified decide endpoint with the decision in the body (Phase
  // 18 adds OVERRIDE alongside approve/reject) instead of V1's
  // path-segment-per-action.
  const res = await authFetch(
    `${API_BASE}/api/v1/recommendations/${recId}/decide`,
    token,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision: action }),
    }
  );
  if (!res.ok) throw new Error(`decide failed: ${res.status}`);
  return res.json();
}

// Backend V2: ingestion is async (202, no synchronous recommendations —
// see docs/BACKEND_V2_FRONTEND_COMPATIBILITY.md). The result arrives later
// over the authenticated /ws/alerts socket, not in this response.
//
// V2 also requires device credentials, not a user bearer token, on
// ingestion endpoints (Phase 7). This demo button is the one place those
// credentials are read from NEXT_PUBLIC_* env vars — acceptable only
// because it is a labelled simulate-a-sensor demo, never how a real
// sensor should authenticate (a real device embeds its own secret, not
// one shipped in browser JS).
export async function ingestWaterLevel(reading: number) {
  const res = await fetch(`${API_BASE}/api/v1/ingestion/iot`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Device-Id": process.env.NEXT_PUBLIC_DEMO_DEVICE_ID ?? "",
      "X-Device-Secret": process.env.NEXT_PUBLIC_DEMO_DEVICE_SECRET ?? "",
    },
    body: JSON.stringify({
      sensor_id: "wl-042",
      metric: "water_level",
      reading,
      unit: "m",
      lat: 13.0827,
      lon: 80.2707,
    }),
  });
  if (!res.ok) throw new Error(`ingest failed: ${res.status}`);
  return res.json() as Promise<{
    event_id: string;
    incident_id: string;
    status: string;
  }>;
}
