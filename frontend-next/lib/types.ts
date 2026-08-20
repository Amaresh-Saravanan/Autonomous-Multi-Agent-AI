export interface Recommendation {
  rec_id: string;
  incident_id: string;
  agent_id: string;
  action: string;
  rationale: string;
  confidence: number;
  severity: number;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  evidence: string[];
  geo?: { type: "Point"; coordinates: [number, number] } | null;
  details?: Record<string, unknown> & {
    route_line?: [number, number][];
    blocked?: boolean;
  };
  target_agency?: string | null;
}

export interface WsAlertsMessage {
  incident_id: string;
  recommendations: Recommendation[];
}

export interface CurrentUser {
  username: string;
  role: "admin" | "operator" | "viewer";
  agency: string;
  exp: number;
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
