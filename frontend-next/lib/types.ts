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

export type ResourcesResponse = Record<ResourceCategory, ResourceItem[]>;

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
