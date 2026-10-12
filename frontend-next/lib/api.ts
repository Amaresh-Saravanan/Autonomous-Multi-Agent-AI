import type {
  AgentHealth,
  AccessRequest,
  AgencyOption,
  IncidentForecast,
  AuditEntry,
  CitizenChatReply,
  CitizenReport,
  Conflict,
  CurrentUser,
  IncidentState,
  IncidentSummary,
  MetricsSummary,
  Recommendation,
  RecommendationStatus,
  ResourcesResponse,
} from "./types";

// Backend V2 base URL. NEXT_PUBLIC_* is inlined at BUILD time, so production
// builds must set NEXT_PUBLIC_API_BASE; the localhost default is dev-only.
export const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8001"
).replace(/\/+$/, "");

// Fired when the backend answers 401 so the auth layer can drop the session
// and send the user back to /login (token expired or revoked).
export const AUTH_EXPIRED_EVENT = "eoc:auth-expired";

// ---------------------------------------------------------------------------
// Wire types (what backend-v2 actually returns) and adapters to the UI types.
// Keeping the mapping in one place means components never see V2 field names.
// ---------------------------------------------------------------------------

interface WireRecommendation {
  id: string;
  incident_id: string;
  agent_id: string;
  action: string;
  priority: string;
  confidence: number;
  reasoning: string;
  target_agency_id: string | null;
  status: string;
  created_at: string;
  severity?: number;
  evidence?: string[];
  details?: Recommendation["details"];
  geo?: Recommendation["geo"];
}

interface WireIncident {
  id: string;
  status: string;
  severity: number;
  latitude: number | null;
  longitude: number | null;
  district: string | null;
  state_region: string | null;
  updated_at: string;
  event_count?: number;
}

interface WireAudit {
  id: string;
  timestamp: string;
  actor_type: string;
  actor_id: string;
  action: string;
  incident_id: string | null;
  recommendation_id: string | null;
  metadata: Record<string, unknown>;
}

interface WireBlackboardEntry {
  severity?: number;
  action?: string | null;
  evidence?: string[];
  rationale?: string;
  confidence?: number;
  details?: Recommendation["details"];
}

// The backend stores UTC. SQLite-backed (dev) deployments serialize naive
// timestamps with no zone designator, which browsers would parse as LOCAL
// time; normalise so a timestamp always means the same instant.
export function utc(ts: string): string {
  return /[zZ]|[+-]\d\d:?\d\d$/.test(ts) ? ts : `${ts}Z`;
}

const KNOWN_STATUSES: RecommendationStatus[] = ["pending", "approved", "rejected", "overridden", "expired"];

export function toRecommendation(w: WireRecommendation): Recommendation {
  const status = w.status.toLowerCase() as RecommendationStatus;
  return {
    rec_id: w.id,
    incident_id: w.incident_id,
    agent_id: w.agent_id,
    action: w.action,
    rationale: w.reasoning,
    confidence: w.confidence,
    severity: w.severity ?? 0,
    status: KNOWN_STATUSES.includes(status) ? status : "pending",
    created_at: utc(w.created_at),
    evidence: w.evidence ?? [],
    geo: w.geo ?? null,
    details: w.details ?? {},
    target_agency: w.target_agency_id,
  };
}

export function toIncidentSummary(w: WireIncident): IncidentSummary {
  return {
    incident_id: w.id,
    lat: w.latitude,
    lon: w.longitude,
    last_ts: Date.parse(utc(w.updated_at)) / 1000,
    count: w.event_count ?? 0,
    state: w.state_region,
    district: w.district,
  };
}

export function toAuditEntry(w: WireAudit): AuditEntry {
  return {
    actor: `${w.actor_type.toLowerCase()}:${w.actor_id}`,
    action: w.action,
    target: w.recommendation_id ?? w.incident_id ?? "—",
    before: {},
    after: w.metadata ?? {},
    timestamp: utc(w.timestamp),
  };
}

function toIncidentState(
  incidentId: string,
  raw: Record<string, unknown> & { conflicts?: Conflict[] }
): IncidentState {
  const state: IncidentState = { conflicts: raw.conflicts ?? [] };
  for (const [agentId, value] of Object.entries(raw)) {
    if (agentId === "conflicts") continue;
    const e = value as WireBlackboardEntry;
    state[agentId] = {
      rec_id: `${incidentId}:${agentId}`,
      incident_id: incidentId,
      agent_id: agentId,
      action: e.action ?? "",
      rationale: e.rationale ?? "",
      confidence: e.confidence ?? 0,
      severity: e.severity ?? 0,
      status: "pending",
      created_at: "",
      evidence: e.evidence ?? [],
      details: e.details ?? {},
    };
  }
  return state;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface LoginResult {
  accessToken: string;
  user: CurrentUser;
}

function jwtExp(token: string): number {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp === "number" ? payload.exp : 0;
  } catch {
    return 0;
  }
}

export async function login(email: string, password: string): Promise<LoginResult> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("invalid credentials");
  const body = await res.json();
  return {
    accessToken: body.access_token as string,
    user: {
      username: (body.email as string | undefined) ?? email,
      role: String(body.role).toLowerCase() as CurrentUser["role"],
      agency: (body.agency_name as string | undefined) ?? String(body.agency_id),
      exp: jwtExp(body.access_token),
      mustChangePassword: Boolean(body.must_change_password),
    },
  };
}

// Wraps fetch with the bearer token; a 401 tells the auth layer the session
// is dead so it can return the user to /login.
export async function authFetch(
  url: string,
  token: string | null,
  opts: RequestInit = {}
): Promise<Response> {
  const headers = {
    ...(opts.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const res = await fetch(url, { ...opts, headers });
  if (res.status === 401 && typeof window !== "undefined") {
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  }
  return res;
}

// ---------------------------------------------------------------------------
// Reads
// ---------------------------------------------------------------------------

export async function fetchResources(token: string | null): Promise<ResourcesResponse> {
  const res = await authFetch(`${API_BASE}/api/v1/resources`, token);
  if (!res.ok) throw new Error(`resources fetch failed: ${res.status}`);
  const body = (await res.json()) as ResourcesResponse;
  // V2 names hospital capacity `beds_total`; the UI reads `capacity`.
  body.hospitals = (body.hospitals ?? []).map((h) => ({ ...h, capacity: h.capacity ?? h.beds_total }));
  return body;
}

export async function fetchRecommendations(token: string | null): Promise<Recommendation[]> {
  const res = await authFetch(`${API_BASE}/api/v1/recommendations`, token);
  if (!res.ok) throw new Error(`recommendations fetch failed: ${res.status}`);
  return ((await res.json()) as WireRecommendation[]).map(toRecommendation);
}

export async function fetchIncidents(token: string | null): Promise<IncidentSummary[]> {
  const res = await authFetch(`${API_BASE}/api/v1/incidents`, token);
  if (!res.ok) throw new Error(`incidents fetch failed: ${res.status}`);
  return ((await res.json()) as WireIncident[]).map(toIncidentSummary);
}

export async function fetchIncidentState(
  token: string | null,
  incidentId: string
): Promise<IncidentState> {
  const res = await authFetch(`${API_BASE}/api/v1/incidents/${incidentId}/state`, token);
  if (!res.ok) throw new Error(`incident state fetch failed: ${res.status}`);
  return toIncidentState(incidentId, await res.json());
}

export async function fetchForecast(token: string | null, incidentId: string): Promise<IncidentForecast> {
  const res = await authFetch(`${API_BASE}/api/v1/incidents/${incidentId}/forecast`, token);
  if (!res.ok) throw new Error(`forecast fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchAudit(token: string | null): Promise<AuditEntry[]> {
  const res = await authFetch(`${API_BASE}/api/v1/audit`, token);
  if (!res.ok) throw new Error(`audit fetch failed: ${res.status}`);
  const rows = ((await res.json()) as WireAudit[]).map(toAuditEntry);
  // The API returns newest-first; AuditPage expects oldest-first and reverses.
  return rows.sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

export async function fetchMetrics(token: string | null): Promise<MetricsSummary> {
  const res = await authFetch(`${API_BASE}/api/v1/metrics`, token);
  if (!res.ok) throw new Error(`metrics fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchAgentHealth(token: string | null): Promise<AgentHealth[]> {
  const res = await authFetch(`${API_BASE}/api/v1/agents/health`, token);
  if (!res.ok) throw new Error(`agent health fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchCitizenReports(
  token: string | null,
  incidentId?: string
): Promise<CitizenReport[]> {
  const url = incidentId
    ? `${API_BASE}/api/v1/citizen/reports?incident_id=${encodeURIComponent(incidentId)}`
    : `${API_BASE}/api/v1/citizen/reports`;
  const res = await authFetch(url, token);
  if (!res.ok) throw new Error(`citizen reports fetch failed: ${res.status}`);
  return ((await res.json()) as CitizenReport[]).map((r) => ({ ...r, timestamp: utc(r.timestamp) }));
}

export async function fetchSeverityGeojson(token: string | null, incidentId: string) {
  const res = await authFetch(`${API_BASE}/api/v1/incidents/${incidentId}/severity`, token);
  if (!res.ok) throw new Error(`severity fetch failed: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Writes
// ---------------------------------------------------------------------------

export async function decideRecommendation(
  token: string | null,
  recId: string,
  action: "approve" | "reject"
): Promise<Recommendation> {
  const res = await authFetch(`${API_BASE}/api/v1/recommendations/${recId}/decide`, token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision: action }),
  });
  if (!res.ok) throw new Error(`decide failed: ${res.status}`);
  return toRecommendation(await res.json());
}

// ---------------------------------------------------------------------------
// Same-origin server proxies (app/api/*). Device credentials for citizen
// chat/reports and the demo sensor live in SERVER env only — they are never
// shipped to the browser.
// ---------------------------------------------------------------------------

export async function postCitizenChat(message: string, language = "en"): Promise<CitizenChatReply> {
  const res = await fetch("/api/citizen-chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, language }),
  });
  if (!res.ok) throw new Error(`citizen chat failed: ${res.status}`);
  const body = await res.json();
  return {
    reply: body.reply,
    language: body.language,
    llm_used: body.reasoning_mode === "llm",
    sources: body.sources ?? [],
    language_fallback: Boolean(body.language_fallback),
  };
}

export async function postCitizenReport(report: {
  message: string;
  claimed_severity: number;
  lat?: number;
  lon?: number;
  reporter_contact?: string;
}): Promise<{ incident_id: string }> {
  const res = await fetch("/api/citizen-report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(report),
  });
  if (!res.ok) throw new Error(`citizen report failed: ${res.status}`);
  return res.json();
}

// Backend V2 ingestion is async (202): recommendations arrive later over the
// authenticated /ws/alerts socket. The demo sensor is proxied server-side,
// operator+ only, and disabled unless DEMO_INGEST_ENABLED=true.
export async function ingestWaterLevel(token: string | null, reading: number) {
  const res = await fetch("/api/demo-ingest", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ reading }),
  });
  if (!res.ok) throw new Error(`ingest failed: ${res.status}`);
  return res.json() as Promise<{ event_id: string; incident_id: string; status: string }>;
}


// ---------------------------------------------------------------------------
// Accounts (SEC-1): public request forms go through same-origin proxies; admin
// review and password change go straight to the API with the bearer token.
// ---------------------------------------------------------------------------

async function postPublic(path: string, body: unknown): Promise<void> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(String(res.status));
}

export const postAccessRequest = (body: {
  email: string;
  full_name: string;
  agency_text?: string;
  requested_role?: "OPERATOR" | "VIEWER";
}) => postPublic("/api/access-request", body);

export const postResetRequest = (email: string) => postPublic("/api/reset-request", { email });

export async function changePassword(token: string | null, current: string, next: string): Promise<void> {
  const res = await authFetch(`${API_BASE}/api/v1/auth/change-password`, token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ current_password: current, new_password: next }),
  });
  if (res.status === 204) return;
  if (res.status === 422) throw new Error("New password must be at least 10 characters and different from the current one.");
  if (res.status === 401) throw new Error("Current password is incorrect.");
  throw new Error("Could not change password.");
}

export async function fetchAccessRequests(token: string | null): Promise<AccessRequest[]> {
  const res = await authFetch(`${API_BASE}/api/v1/access/requests`, token);
  if (!res.ok) throw new Error(`access requests fetch failed: ${res.status}`);
  return res.json();
}

export async function fetchAgencies(token: string | null): Promise<AgencyOption[]> {
  const res = await authFetch(`${API_BASE}/api/v1/access/agencies`, token);
  if (!res.ok) throw new Error(`agencies fetch failed: ${res.status}`);
  return res.json();
}

export async function approveAccessRequest(
  token: string | null,
  id: string,
  opts: { agency_id?: string; role?: string }
): Promise<{ email: string; temporary_password: string }> {
  const res = await authFetch(`${API_BASE}/api/v1/access/requests/${id}/approve`, token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(opts),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.error?.message ?? detail?.message ?? `approve failed: ${res.status}`);
  }
  return res.json();
}

export async function rejectAccessRequest(token: string | null, id: string): Promise<void> {
  const res = await authFetch(`${API_BASE}/api/v1/access/requests/${id}/reject`, token, { method: "POST" });
  if (!res.ok) throw new Error(`reject failed: ${res.status}`);
}
