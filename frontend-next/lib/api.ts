import type {
  CitizenReport,
  CurrentUser,
  IncidentState,
  Recommendation,
  ResourcesResponse,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export function decodeJwtPayload(token: string): CurrentUser {
  return JSON.parse(atob(token.split(".")[1]));
}

export async function login(
  username: string,
  password: string
): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
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
  const res = await authFetch(`${API_BASE}/resources`, token);
  if (!res.ok) throw new Error(`resources fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchIncidentState(
  token: string | null,
  incidentId: string
): Promise<IncidentState> {
  const res = await authFetch(`${API_BASE}/incidents/${incidentId}`, token);
  if (!res.ok) throw new Error(`incident state fetch failed: ${res.status}`);
  return res.json();
}

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
  const res = await authFetch(
    `${API_BASE}/recommendations/${recId}/${action}`,
    token,
    { method: "POST" }
  );
  if (!res.ok) throw new Error(`decide failed: ${res.status}`);
  return res.json();
}

export async function ingestWaterLevel(reading: number) {
  const res = await fetch(`${API_BASE}/ingest/iot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      sensor_id: "wl-042",
      metric: "water_level",
      reading,
      unit: "m",
      lat: 13.0827,
      lon: 80.2707,
      incident_id: "demo-1",
    }),
  });
  return res.json() as Promise<{
    event_id: string;
    incident_id: string;
    recommendations: Recommendation[];
  }>;
}
