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
