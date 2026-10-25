// ponytail: presentation-only mock telemetry generator. There is no
// backend endpoint to list ingestion devices or replay received events
// (see docs/MIGRATION_TRACKER.md — only POST /api/v1/ingestion/* exists,
// write-only, device-authenticated). Swap this module for a real fetch
// once a GET events/devices endpoint ships.

export type SourceType = "iot" | "weather" | "satellite" | "citizen";

export interface MockStation {
  id: string;
  source_type: SourceType;
  label: string;
  lat: number;
  lon: number;
}

export const SOURCE_LABELS: Record<SourceType, string> = {
  iot: "IoT Sensor",
  weather: "Weather Station",
  satellite: "Satellite Pass",
  citizen: "Citizen Report",
};

export const SOURCE_ENDPOINTS: Record<SourceType, string> = {
  iot: "/api/v1/ingestion/iot",
  weather: "/api/v1/ingestion/weather",
  satellite: "/api/v1/ingestion/satellite",
  citizen: "/api/v1/ingestion/citizen",
};

export const SOURCE_COLORS: Record<SourceType, string> = {
  iot: "#22C55E",
  weather: "#3B82F6",
  satellite: "#A855F7",
  citizen: "#F97316",
};

// Fixed station locations around Chennai (matches the demo-ingest button's
// hardcoded lat/lon) so the Map and Data Sources pages agree on "where this
// comes from".
export const MOCK_STATIONS: MockStation[] = [
  { id: "wl-042", source_type: "iot", label: "Water Level Sensor WL-042", lat: 13.0827, lon: 80.2707 },
  { id: "wl-017", source_type: "iot", label: "Water Level Sensor WL-017", lat: 13.0475, lon: 80.2219 },
  { id: "ws-04", source_type: "weather", label: "Weather Station WS-04", lat: 13.1143, lon: 80.291 },
  { id: "sat-pass-114", source_type: "satellite", label: "Satellite Pass 114", lat: 13.021, lon: 80.2412 },
  { id: "citizen-tnagar", source_type: "citizen", label: "Citizen Reports — T. Nagar", lat: 13.0418, lon: 80.2341 },
  { id: "citizen-adyar", source_type: "citizen", label: "Citizen Reports — Adyar", lat: 13.0012, lon: 80.2565 },
];

function rand(min: number, max: number): number {
  return Math.random() * (max - min) + min;
}

function mockPayload(station: MockStation): Record<string, unknown> {
  switch (station.source_type) {
    case "iot":
      return {
        sensor_id: station.id,
        metric: "water_level",
        reading: Number(rand(0.4, 3.2).toFixed(2)),
        unit: "m",
      };
    case "weather":
      return {
        location: station.label,
        temp_c: Number(rand(26, 34).toFixed(1)),
        humidity_pct: Math.round(rand(55, 95)),
        wind_speed_kmh: Math.round(rand(10, 60)),
      };
    case "satellite":
      return {
        image_id: `IMG-${Math.floor(rand(10000, 99999))}`,
        cloud_cover_pct: Math.round(rand(5, 80)),
        resolution_m: 10,
      };
    case "citizen":
      return {
        message: "Water rising near main road",
        claimed_severity: Number(rand(0.3, 0.9).toFixed(2)),
      };
  }
}

export interface MockEvent {
  id: string;
  station: MockStation;
  payload: Record<string, unknown>;
  latency_ms: number;
  timestamp: string;
}

let seq = 0;

export function nextMockEvent(): MockEvent {
  seq += 1;
  const station = MOCK_STATIONS[Math.floor(Math.random() * MOCK_STATIONS.length)];
  return {
    id: `evt-${Date.now()}-${seq}`,
    station,
    payload: mockPayload(station),
    latency_ms: Math.round(rand(40, 190)),
    timestamp: new Date().toISOString(),
  };
}
