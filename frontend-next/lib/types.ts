export type RecommendationStatus = "pending" | "approved" | "rejected" | "overridden" | "expired";

export interface Recommendation {
  rec_id: string;
  incident_id: string;
  agent_id: string;
  action: string;
  rationale: string;
  confidence: number;
  severity: number;
  status: RecommendationStatus;
  created_at: string;
  evidence: string[];
  geo?: { type: "Point"; coordinates: [number, number] } | null;
  details?: Record<string, unknown> & {
    route_line?: [number, number][];
    blocked?: boolean;
  };
  target_agency?: string | null;
}

// V2: no inline `recommendations` — the socket carries the alert only;
// the frontend re-fetches recommendations on receipt (see
// docs/archive/BACKEND_V2_FRONTEND_COMPATIBILITY.md).
export interface WsAlertsMessage {
  alert_id: string;
  incident_id: string;
  level: string;
  message: string;
}

// Built client-side at login from the V2 token response (the JWT itself only
// carries sub/role/agency_id/exp). `role` is lower-cased for the UI's rank map.
export interface CurrentUser {
  username: string; // login email
  role: "admin" | "operator" | "viewer";
  agency: string; // agency display name (falls back to id)
  exp: number; // epoch seconds, from the JWT
  mustChangePassword?: boolean; // admin-issued temporary password
}

export interface ResourceItem {
  id: string;
  name?: string;
  lat: number;
  lon: number;
  [key: string]: unknown;
}

export type ResourceCategory = "hospitals" | "shelters" | "teams" | "ambulances";

// supplies added via BE-3 (tracker 3.11.6.5) — food/water/blankets counts,
// not per-item like the other four categories.
export type ResourcesResponse = Record<ResourceCategory, ResourceItem[]> & {
  supplies?: Record<string, number>;
};

export interface Conflict {
  agents: string[];
  target: string;
  values: Record<string, string>;
  recs: string[];
  rationale: string;
}

// GET /incidents/{id} returns the raw blackboard: one Recommendation per
// agent id that has reported, plus a "conflicts" array (AC-4).
export interface IncidentState {
  conflicts?: Conflict[];
  [agentId: string]: Recommendation | Conflict[] | undefined;
}

// GET /incidents (tracker 3.11.6.2 / BE-1) — one row per known incident.
export interface IncidentSummary {
  incident_id: string;
  lat: number | null;
  lon: number | null;
  last_ts: number; // epoch seconds
  count: number;
  state: string | null;
  district: string | null;
}

// GET /metrics (tracker 3.8, operator+).
export interface MetricsSummary {
  routes: Record<string, { count: number; avg_latency_ms: number; p95_latency_ms: number }>;
  recommendation_acceptance_rate: number | null;
}

// POST /citizen/chat (AG-7, open endpoint — tracker 3.11.6.8).
export interface CitizenChatReply {
  reply: string;
  language: string;
  llm_used: boolean;
  sources?: string[];
  /** True when the reply is not in the language the citizen asked for. */
  language_fallback?: boolean;
}

// GET /api/v1/agents/health (PRD resilience: agent failures are visible).
export interface AgentHealth {
  agent_id: string;
  status: string;
  last_run: string | null;
  execution_count: number;
  failure_count: number;
  average_latency_ms: number;
  degraded_mode: boolean;
  last_error: string | null;
}

// GET /audit (tracker 3.11.6.10 / BE-2, admin-only).
export interface AuditEntry {
  actor: string;
  action: string;
  target: string;
  before: Record<string, unknown>;
  after: Record<string, unknown>;
  timestamp: string;
}

export interface CitizenReport {
  event_id: string;
  incident_id: string;
  reporter_id: string;
  message: string;
  claimed_severity: number;
  confidence: number;
  flagged_for_review: boolean;
  timestamp: string;
}

export interface ForecastHorizon {
  hours: number;
  predicted_value: number;
  predicted_severity: number;
}

// PRD DS-2. `insufficient_data` is a normal answer, not an error.
export interface IncidentForecast {
  status: "ok" | "insufficient_data";
  metric: string;
  method: string;
  n_points: number;
  reason?: string;
  sensor_id?: string;
  unit?: string;
  trend?: "rising" | "falling" | "steady";
  slope_per_hour?: number;
  current_value?: number;
  current_severity?: number;
  fit_r2?: number;
  confidence?: "low" | "moderate";
  as_of?: string;
  horizons: ForecastHorizon[];
  disclaimer?: string;
}

// SEC-1 access requests (admin-approved signup / password reset).
export interface AccessRequest {
  id: string;
  kind: "SIGNUP" | "RESET";
  status: "PENDING" | "APPROVED" | "REJECTED";
  email: string;
  full_name: string | null;
  agency_text: string | null;
  requested_role: string | null;
  created_at: string | null;
  decided_at: string | null;
}

export interface AgencyOption {
  id: string;
  name: string;
}
