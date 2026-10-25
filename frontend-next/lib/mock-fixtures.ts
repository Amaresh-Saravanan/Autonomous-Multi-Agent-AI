// ponytail: static-ish fixtures for NEXT_PUBLIC_MOCK_DATA=true (presentation
// mode). Mirrors the shapes lib/api.ts normally builds from backend-v2 wire
// responses — swap out when every section has a real, working data path
// (today several don't: no events-by-id endpoint, worker queue needs Redis).
// Timestamps are computed relative to module load so a demo run on any date
// still reads as "just happened" instead of a fixed past date.

import type {
  AccessRequest,
  AgencyOption,
  AgentHealth,
  AuditEntry,
  Conflict,
  CitizenReport,
  IncidentForecast,
  IncidentState,
  IncidentSummary,
  MetricsSummary,
  Recommendation,
  ResourcesResponse,
} from "./types";

export const INC_1 = "incident-demo-001"; // Chennai Central flood
export const INC_2 = "incident-demo-002"; // Adyar storm, early triage

const NOW = Date.now();
function minutesAgo(mins: number): string {
  return new Date(NOW - mins * 60_000).toISOString();
}
function epoch(iso: string): number {
  return Date.parse(iso) / 1000;
}

export const MOCK_RECOMMENDATIONS: Recommendation[] = [
  {
    rec_id: "rec-demo-ag1-1",
    incident_id: INC_1,
    agent_id: "AG-1",
    action: "classify_disaster",
    rationale:
      "Water level sensor WL-042 reading 2.8m, 1.4m above flood threshold. Classified as FLOOD; severity trending up.",
    confidence: 0.91,
    severity: 0.88,
    status: "approved",
    created_at: minutesAgo(48),
    evidence: ["evt-wl042-014", "evt-wl042-015"],
    geo: { type: "Point", coordinates: [80.2707, 13.0827] },
    details: {},
    target_agency: null,
  },
  {
    rec_id: "rec-demo-ag2-1",
    incident_id: INC_1,
    agent_id: "AG-2",
    action: "assess_damage",
    rationale: "Satellite pass 114 shows standing water across 3 city blocks; an estimated 120 structures affected.",
    confidence: 0.78,
    severity: 0.82,
    status: "approved",
    created_at: minutesAgo(42),
    evidence: ["evt-sat-114-07"],
    geo: { type: "Point", coordinates: [80.269, 13.081] },
    details: {},
    target_agency: null,
  },
  {
    rec_id: "rec-demo-ag3-1",
    incident_id: INC_1,
    agent_id: "AG-3",
    action: "dispatch_rescue_team",
    rationale: "Two residential blocks isolated by flood water. Recommend water-rescue Team R-04 with boat support.",
    confidence: 0.85,
    severity: 0.9,
    status: "pending",
    created_at: minutesAgo(39),
    evidence: ["evt-wl042-015", "evt-citizen-001"],
    geo: { type: "Point", coordinates: [80.268, 13.078] },
    details: {},
    target_agency: "city_emergency_mgmt",
  },
  {
    rec_id: "rec-demo-ag4-1",
    incident_id: INC_1,
    agent_id: "AG-4",
    action: "alert_hospital",
    rationale:
      "Elevated risk of waterborne injury in the affected zone. City General Hospital (12 free beds) placed on standby.",
    confidence: 0.8,
    severity: 0.7,
    status: "approved",
    created_at: minutesAgo(36),
    evidence: ["evt-sat-114-07", "evt-citizen-001"],
    geo: { type: "Point", coordinates: [80.265, 13.07] },
    details: {},
    target_agency: "regional_health_dept",
  },
  {
    rec_id: "rec-demo-ag5-1",
    incident_id: INC_1,
    agent_id: "AG-5",
    action: "allocate_resources",
    rationale: "Allocating 2 ambulances and 200 shelter beds to the affected zone.",
    confidence: 0.83,
    severity: 0.8,
    status: "pending",
    created_at: minutesAgo(33),
    evidence: ["evt-wl042-015"],
    geo: { type: "Point", coordinates: [80.272, 13.075] },
    details: {},
    target_agency: "city_emergency_mgmt",
  },
  {
    rec_id: "rec-demo-ag6-1",
    incident_id: INC_1,
    agent_id: "AG-6",
    action: "reroute_traffic",
    rationale: "Main Road blocked by flood water; rerouting via the Anna Salai bypass.",
    confidence: 0.76,
    severity: 0.75,
    status: "approved",
    created_at: minutesAgo(30),
    evidence: ["evt-wl042-015"],
    geo: { type: "Point", coordinates: [80.265, 13.079] },
    details: {
      route_line: [
        [80.2707, 13.0827],
        [80.265, 13.079],
        [80.26, 13.075],
      ],
      blocked: true,
    },
    target_agency: null,
  },
  {
    rec_id: "rec-demo-ag8-1",
    incident_id: INC_1,
    agent_id: "AG-8",
    action: "situation_summary",
    rationale:
      "Flood event active 45 minutes. Severity trending up (+0.12/hr). AG-7 running on rule-based fallback (no LLM key).",
    confidence: 0.7,
    severity: 0.85,
    status: "pending",
    created_at: minutesAgo(27),
    evidence: ["evt-wl042-014", "evt-sat-114-07"],
    geo: null,
    details: {},
    target_agency: null,
  },
  // Second, lower-severity incident still in early triage.
  {
    rec_id: "rec-demo-ag1-2",
    incident_id: INC_2,
    agent_id: "AG-1",
    action: "classify_disaster",
    rationale:
      "Citizen report corroborated by nearby Weather Station WS-04 (wind 42km/h, heavy rain). Classified as STORM; confidence low pending more sensor data.",
    confidence: 0.58,
    severity: 0.45,
    status: "pending",
    created_at: minutesAgo(95),
    evidence: ["evt-citizen-002", "evt-ws04-003"],
    geo: { type: "Point", coordinates: [80.2565, 13.0012] },
    details: {},
    target_agency: null,
  },
  {
    rec_id: "rec-demo-ag6-2",
    incident_id: INC_2,
    agent_id: "AG-6",
    action: "monitor_route",
    rationale: "Adyar bridge approach clear; no rerouting needed yet.",
    confidence: 0.6,
    severity: 0.3,
    status: "approved",
    created_at: minutesAgo(90),
    evidence: ["evt-citizen-002"],
    geo: { type: "Point", coordinates: [80.254, 13.003] },
    details: {
      route_line: [
        [80.2565, 13.0012],
        [80.254, 13.003],
      ],
      blocked: false,
    },
    target_agency: null,
  },
];

const MOCK_CONFLICTS: Record<string, Conflict[]> = {
  [INC_1]: [
    {
      agents: ["AG-3", "AG-5"],
      target: "city_emergency_mgmt",
      values: { AG_3: "water-rescue team + boat", AG_5: "ambulance + shelter beds" },
      recs: ["rec-demo-ag3-1", "rec-demo-ag5-1"],
      rationale: "AG-3 and AG-5 both targeted the same agency with different resource requests in the same window.",
    },
  ],
};

export const MOCK_INCIDENTS: IncidentSummary[] = [
  {
    incident_id: INC_1,
    lat: 13.0827,
    lon: 80.2707,
    last_ts: epoch(minutesAgo(27)),
    count: 14,
    state: "Tamil Nadu",
    district: "Chennai Central",
  },
  {
    incident_id: INC_2,
    lat: 13.0012,
    lon: 80.2565,
    last_ts: epoch(minutesAgo(90)),
    count: 3,
    state: "Tamil Nadu",
    district: "Adyar",
  },
];

export function mockIncidentState(incidentId: string): IncidentState {
  const state: IncidentState = { conflicts: MOCK_CONFLICTS[incidentId] ?? [] };
  MOCK_RECOMMENDATIONS.filter((r) => r.incident_id === incidentId).forEach((r) => {
    state[r.agent_id] = r;
  });
  return state;
}

const MOCK_FORECASTS: Record<string, IncidentForecast> = {
  [INC_1]: {
    status: "ok",
    metric: "water_level",
    method: "linear_regression",
    n_points: 12,
    sensor_id: "wl-042",
    unit: "m",
    trend: "rising",
    slope_per_hour: 0.18,
    current_value: 2.8,
    current_severity: 0.88,
    fit_r2: 0.91,
    confidence: "moderate",
    as_of: minutesAgo(20),
    horizons: [
      { hours: 1, predicted_value: 2.98, predicted_severity: 0.9 },
      { hours: 3, predicted_value: 3.34, predicted_severity: 0.95 },
      { hours: 6, predicted_value: 3.88, predicted_severity: 0.99 },
    ],
    disclaimer: "Projection based on limited sensor history — treat as directional, not exact.",
  },
  [INC_2]: {
    status: "insufficient_data",
    metric: "wind_speed",
    method: "linear_regression",
    n_points: 2,
    reason: "Fewer than 5 readings available for this incident yet.",
    horizons: [],
  },
};

export function mockForecast(incidentId: string): IncidentForecast {
  return (
    MOCK_FORECASTS[incidentId] ?? {
      status: "insufficient_data",
      metric: "unknown",
      method: "linear_regression",
      n_points: 0,
      reason: "No sensor history for this incident.",
      horizons: [],
    }
  );
}

const MOCK_CITIZEN_REPORTS: CitizenReport[] = [
  {
    event_id: "evt-citizen-001",
    incident_id: INC_1,
    reporter_id: "anon-7781",
    message: "Water entering ground floor on Mount Road, need help.",
    claimed_severity: 0.85,
    confidence: 0.8,
    flagged_for_review: false,
    timestamp: minutesAgo(45),
  },
  {
    event_id: "evt-citizen-003",
    incident_id: INC_1,
    reporter_id: "anon-9043",
    message: "Report says minor puddling only near the same block, seems exaggerated.",
    claimed_severity: 0.2,
    confidence: 0.2,
    flagged_for_review: true,
    timestamp: minutesAgo(40),
  },
  {
    event_id: "evt-citizen-002",
    incident_id: INC_2,
    reporter_id: "anon-2214",
    message: "Strong winds knocked down a tree near Adyar bridge.",
    claimed_severity: 0.5,
    confidence: 0.5,
    flagged_for_review: false,
    timestamp: minutesAgo(97),
  },
];

export function mockCitizenReports(incidentId?: string): CitizenReport[] {
  return incidentId ? MOCK_CITIZEN_REPORTS.filter((r) => r.incident_id === incidentId) : MOCK_CITIZEN_REPORTS;
}

export const MOCK_AUDIT_ENTRIES: AuditEntry[] = [
  {
    actor: "admin:admin@example.com",
    action: "approve_access_request",
    target: "req-mock-3",
    before: { status: "PENDING" },
    after: { status: "APPROVED", role: "OPERATOR" },
    timestamp: minutesAgo(960),
  },
  {
    actor: "operator:ops1@example.com",
    action: "approve",
    target: "rec-demo-ag1-1",
    before: { status: "pending" },
    after: { status: "approved" },
    timestamp: minutesAgo(47),
  },
  {
    actor: "operator:ops1@example.com",
    action: "approve",
    target: "rec-demo-ag2-1",
    before: { status: "pending" },
    after: { status: "approved" },
    timestamp: minutesAgo(41),
  },
  {
    actor: "operator:ops1@example.com",
    action: "approve",
    target: "rec-demo-ag4-1",
    before: { status: "pending" },
    after: { status: "approved" },
    timestamp: minutesAgo(35),
  },
  {
    actor: "operator:ops1@example.com",
    action: "approve",
    target: "rec-demo-ag6-1",
    before: { status: "pending" },
    after: { status: "approved" },
    timestamp: minutesAgo(29),
  },
];

export const MOCK_METRICS: MetricsSummary = {
  routes: {
    "/api/v1/ingestion/iot": { count: 42, avg_latency_ms: 38, p95_latency_ms: 95 },
    "/api/v1/ingestion/weather": { count: 18, avg_latency_ms: 44, p95_latency_ms: 110 },
    "/api/v1/ingestion/satellite": { count: 6, avg_latency_ms: 210, p95_latency_ms: 340 },
    "/api/v1/ingestion/citizen": { count: 11, avg_latency_ms: 52, p95_latency_ms: 120 },
    "/api/v1/recommendations": { count: 134, avg_latency_ms: 22, p95_latency_ms: 58 },
  },
  recommendation_acceptance_rate: 0.78,
};

export const MOCK_AGENT_HEALTH: AgentHealth[] = [
  { agent_id: "AG-1", status: "OK", last_run: minutesAgo(27), execution_count: 212, failure_count: 0, average_latency_ms: 85, degraded_mode: false, last_error: null },
  { agent_id: "AG-2", status: "OK", last_run: minutesAgo(42), execution_count: 198, failure_count: 1, average_latency_ms: 310, degraded_mode: false, last_error: null },
  { agent_id: "AG-3", status: "OK", last_run: minutesAgo(39), execution_count: 64, failure_count: 0, average_latency_ms: 92, degraded_mode: false, last_error: null },
  { agent_id: "AG-4", status: "OK", last_run: minutesAgo(36), execution_count: 71, failure_count: 0, average_latency_ms: 78, degraded_mode: false, last_error: null },
  { agent_id: "AG-5", status: "OK", last_run: minutesAgo(33), execution_count: 71, failure_count: 0, average_latency_ms: 66, degraded_mode: false, last_error: null },
  { agent_id: "AG-6", status: "OK", last_run: minutesAgo(30), execution_count: 59, failure_count: 0, average_latency_ms: 140, degraded_mode: false, last_error: null },
  { agent_id: "AG-7", status: "DEGRADED", last_run: minutesAgo(25), execution_count: 58, failure_count: 2, average_latency_ms: 140, degraded_mode: true, last_error: "LLM provider unavailable; using rule-based fallback" },
  { agent_id: "AG-8", status: "OK", last_run: minutesAgo(27), execution_count: 212, failure_count: 0, average_latency_ms: 55, degraded_mode: false, last_error: null },
];

export const MOCK_RESOURCES: ResourcesResponse = {
  hospitals: [
    { id: "hosp-1", name: "City General Hospital", lat: 13.07, lon: 80.265, capacity: 40, beds_total: 40, free_beds: 12 },
    { id: "hosp-2", name: "Adyar Community Hospital", lat: 13.005, lon: 80.258, capacity: 15, beds_total: 15, free_beds: 2 },
  ],
  shelters: [
    { id: "shelter-1", name: "Chennai Central Relief Shelter", lat: 13.08, lon: 80.275, capacity: 200, occupied: 85 },
    { id: "shelter-2", name: "T. Nagar Community Hall", lat: 13.041, lon: 80.234, capacity: 120, occupied: 40 },
  ],
  teams: [
    { id: "team-r04", name: "Water Rescue Team R-04", lat: 13.078, lon: 80.268, status: "dispatched" },
    { id: "team-m02", name: "Medical Response Team M-02", lat: 13.05, lon: 80.24, status: "standby" },
  ],
  ambulances: [
    { id: "amb-11", name: "Ambulance 11", lat: 13.083, lon: 80.271, status: "en route" },
    { id: "amb-12", name: "Ambulance 12", lat: 13.002, lon: 80.255, status: "available" },
  ],
  supplies: { food: 5000, water: 12000, blankets: 800 },
};

function gridCell(lat: number, lon: number, d: number, severity: number): GeoJSON.Feature {
  return {
    type: "Feature",
    properties: { severity },
    geometry: {
      type: "Polygon",
      coordinates: [
        [
          [lon - d, lat - d],
          [lon + d, lat - d],
          [lon + d, lat + d],
          [lon - d, lat + d],
          [lon - d, lat - d],
        ],
      ],
    },
  };
}

const MOCK_SEVERITY_GEOJSON: Record<string, GeoJSON.FeatureCollection> = {
  [INC_1]: {
    type: "FeatureCollection",
    features: [
      gridCell(13.0827, 80.2707, 0.01, 0.92),
      gridCell(13.079, 80.265, 0.01, 0.78),
      gridCell(13.075, 80.26, 0.01, 0.55),
    ],
  },
  [INC_2]: {
    type: "FeatureCollection",
    features: [gridCell(13.0012, 80.2565, 0.008, 0.45)],
  },
};

export function mockSeverityGeojson(incidentId: string): GeoJSON.FeatureCollection {
  return MOCK_SEVERITY_GEOJSON[incidentId] ?? { type: "FeatureCollection", features: [] };
}

export const MOCK_ACCESS_REQUESTS: AccessRequest[] = [
  {
    id: "req-mock-1",
    kind: "SIGNUP",
    status: "PENDING",
    email: "new.operator@example.com",
    full_name: "Priya Raman",
    agency_text: "City Emergency Management",
    requested_role: "OPERATOR",
    created_at: minutesAgo(140),
    decided_at: null,
  },
  {
    id: "req-mock-2",
    kind: "RESET",
    status: "PENDING",
    email: "viewer@example.com",
    full_name: null,
    agency_text: null,
    requested_role: null,
    created_at: minutesAgo(180),
    decided_at: null,
  },
  {
    id: "req-mock-3",
    kind: "SIGNUP",
    status: "APPROVED",
    email: "ops2@example.com",
    full_name: "Karthik Subramaniam",
    agency_text: "Regional Health Department",
    requested_role: "OPERATOR",
    created_at: minutesAgo(1020),
    decided_at: minutesAgo(960),
  },
];

export const MOCK_AGENCIES: AgencyOption[] = [
  { id: "agency-1", name: "City Emergency Management" },
  { id: "agency-2", name: "Regional Health Department" },
];
