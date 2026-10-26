"use client";

import { useEffect, useRef } from "react";
import {
  Map as MaplibreMap,
  Marker,
  Popup,
  setWorkerUrl,
  type GeoJSONSource,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type {
  IncidentSummary,
  Recommendation,
  ResourceCategory,
  ResourcesResponse,
} from "@/lib/types";
import { MOCK_STATIONS, SOURCE_COLORS, SOURCE_LABELS } from "@/lib/mock-data-sources";

// maplibre-gl builds its worker URL as `new URL("./maplibre-gl-worker.mjs",
// import.meta.url)` with a dynamically constructed filename, which bundlers
// (webpack, Turbopack) can't statically detect to copy into the build output
// — the worker 404s silently and every tile request just hangs forever with
// no error. Pointing it at a manually-copied static copy (public/) is
// maplibre-gl's own documented workaround for this.
setWorkerUrl("/maplibre-gl-worker.mjs");

const RESOURCE_COLORS: Record<ResourceCategory, string> = {
  hospitals: "#EF4444",
  shelters: "#3B82F6",
  teams: "#A855F7",
  ambulances: "#F97316",
};

// ---------------------------------------------------------------------------
// Marker elements. maplibre sets `transform` on the element it is given to
// position it, so each marker is an empty host div (owned by maplibre) with the
// visual as its child. Severity is shown by colour AND shape: critical =
// solid + halo, high = solid, medium = ring, low = small dot.
// Hex values mirror the --sev-* tokens (CSS vars can't be used in maplibre
// paint, and these are plain DOM nodes built outside React).
// ---------------------------------------------------------------------------
const SEV_HEX = { critical: "#EF4444", high: "#F97316", moderate: "#EAB308", low: "#22C55E" };
const MARKER_GAP = "#0B0E14"; // ground colour used for the ring that separates a marker from the map
const PRIMARY_HEX = "#adc6ff"; // --color-console-primary (dark)

function wrapMarker(inner: HTMLElement): HTMLElement {
  const host = document.createElement("div");
  host.appendChild(inner);
  return host;
}

function severityMarkerEl(sev: number): HTMLElement {
  const dot = document.createElement("div");
  dot.style.borderRadius = "50%";
  dot.style.boxSizing = "border-box";
  let size = 10;
  if (sev >= 0.85) {
    size = 16;
    dot.style.background = SEV_HEX.critical;
    dot.style.border = `2.5px solid ${MARKER_GAP}`;
    dot.style.boxShadow = `0 0 0 6px ${SEV_HEX.critical}40`;
  } else if (sev >= 0.5) {
    size = 14;
    dot.style.background = SEV_HEX.high;
    dot.style.border = `2.5px solid ${MARKER_GAP}`;
  } else if (sev >= 0.3) {
    size = 14;
    dot.style.background = MARKER_GAP;
    dot.style.border = `3px solid ${SEV_HEX.moderate}`;
  } else {
    dot.style.background = SEV_HEX.low;
    dot.style.border = `2px solid ${MARKER_GAP}`;
  }
  dot.style.width = dot.style.height = `${size}px`;
  return wrapMarker(dot);
}

// GET /incidents doesn't carry severity into IncidentSummary yet, so incident
// pins are neutral rings; the selected one is filled with the primary colour
// and a dashed halo.
function incidentMarkerEl(selected: boolean): HTMLElement {
  const dot = document.createElement("div");
  const color = selected ? PRIMARY_HEX : "#8c909f";
  dot.style.cssText = `width:14px;height:14px;box-sizing:border-box;border-radius:50%;border:3px solid ${color};background:${selected ? PRIMARY_HEX : MARKER_GAP};`;
  if (selected) {
    dot.style.outline = `1.5px dashed ${PRIMARY_HEX}`;
    dot.style.outlineOffset = "5px";
  }
  return wrapMarker(dot);
}

const RESOURCE_GLYPH: Record<ResourceCategory, string> = {
  hospitals: "M12 6v12M6 12h12",
  shelters: "M4 12l8-7 8 7v7H4z",
  teams: "M12 7.5a2.5 2.5 0 1 0 .01 0M7.5 18c0-2.6 2-4.2 4.5-4.2s4.5 1.6 4.5 4.2",
  ambulances: "M3 8h11v8H3zM14 11h4l3 3v2h-7z",
};

function resourceMarkerEl(category: ResourceCategory, color: string): HTMLElement {
  const box = document.createElement("div");
  box.style.cssText = `width:20px;height:20px;box-sizing:border-box;border-radius:5px;background:#151B27;border:1.5px solid ${color};display:flex;align-items:center;justify-content:center;`;
  box.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${RESOURCE_GLYPH[category]}"/></svg>`;
  return wrapMarker(box);
}

function sourceMarkerEl(color: string): HTMLElement {
  const diamond = document.createElement("div");
  diamond.style.cssText = `width:10px;height:10px;box-sizing:border-box;background:${color};border:2px solid ${MARKER_GAP};transform:rotate(45deg);`;
  return wrapMarker(diamond);
}

interface MapViewProps {
  resources: ResourcesResponse | null;
  recommendations: Recommendation[];
  severityGeojson: GeoJSON.FeatureCollection | null;
  layersVisible: { severity: boolean; routes: boolean; resources: boolean; dataSources: boolean };
  // Optional: incident pins (tracker 3.11.5 /map). Dashboard's /command usage
  // omits these and behaves exactly as before.
  incidents?: IncidentSummary[];
  selectedIncidentId?: string | null;
  onSelectIncident?: (incidentId: string) => void;
}

// Deepens CARTO Dark Matter's default blacks/grays to match this dashboard's
// own token palette instead of the stock basemap colors: near-black land, a
// blue-tinted water body, low-contrast roads and labels so incident markers
// are the brightest thing on the map.
function tuneBasemapPalette(map: MaplibreMap) {
  const style = map.getStyle();
  style.layers.forEach((layer) => {
    try {
      if (layer.type === "background") {
        map.setPaintProperty(layer.id, "background-color", "#0F131B");
      } else if (layer.type === "fill" && layer.id === "water") {
        map.setPaintProperty(layer.id, "fill-color", "#0A1626");
      } else if (
        layer.type === "fill" &&
        (layer.id.includes("landuse") ||
          layer.id.includes("landcover") ||
          layer.id.includes("park"))
      ) {
        map.setPaintProperty(layer.id, "fill-color", "#111620");
      } else if (layer.type === "line" && layer.id.includes("road")) {
        map.setPaintProperty(layer.id, "line-color", "#232B3D");
      } else if (layer.type === "symbol") {
        map.setPaintProperty(layer.id, "text-color", "#5B6682");
        map.setPaintProperty(layer.id, "text-halo-color", "#0F131B");
      }
    } catch {
      // not every layer accepts the paint prop we tried
    }
  });
}

// Basemap style. Defaults to CARTO's public dark style (third-party, subject to
// its terms and availability); set NEXT_PUBLIC_MAP_STYLE_URL to a self-hosted
// or licensed MapLibre style for production.
const DEFAULT_MAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

export default function MapView({
  resources,
  recommendations,
  severityGeojson,
  layersVisible,
  incidents,
  selectedIncidentId,
  onSelectIncident,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MaplibreMap | null>(null);
  const loadedRef = useRef(false);
  const resourceMarkersRef = useRef<Marker[]>([]);
  const incidentMarkersRef = useRef<Marker[]>([]);
  const recMarkersRef = useRef<Map<string, Marker>>(new Map());
  const dataSourceMarkersRef = useRef<Marker[]>([]);

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new MaplibreMap({
      container: containerRef.current,
      style: process.env.NEXT_PUBLIC_MAP_STYLE_URL || DEFAULT_MAP_STYLE,
      center: [80.2707, 13.0827],
      zoom: 10,
      pitch: 0,
    });
    mapRef.current = map;

    map.on("load", () => {
      tuneBasemapPalette(map);
      map.addSource("severity", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "severity-fill",
        type: "fill",
        source: "severity",
        paint: {
          "fill-color": [
            "interpolate",
            ["linear"],
            ["get", "severity"],
            0,
            "#22C55E",
            0.5,
            "#EAB308",
            0.85,
            "#F97316",
            1,
            "#EF4444",
          ],
          "fill-opacity": 0.35,
        },
      });
      map.addSource("routes", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "routes-line",
        type: "line",
        source: "routes",
        paint: {
          "line-color": ["case", ["get", "blocked"], "#EF4444", "#22C55E"],
          "line-width": 3,
        },
      });
      // Data source station pins — mock telemetry origins, static positions
      // (lib/mock-data-sources.ts); fine to add once at map load since they
      // don't depend on any fetched prop. Initial visibility is applied here
      // directly (not left to the toggle effect below) since pages that
      // never change layersVisible.dataSources after mount (e.g. RoutesPage)
      // would otherwise never get a second effect run to apply it.
      dataSourceMarkersRef.current = MOCK_STATIONS.map((station) => {
        const marker = new Marker({ element: sourceMarkerEl(SOURCE_COLORS[station.source_type]) })
          .setLngLat([station.lon, station.lat])
          .setPopup(new Popup({ offset: 14 }).setText(`${SOURCE_LABELS[station.source_type]}: ${station.label}`))
          .addTo(map);
        marker.getElement().style.display = layersVisible.dataSources ? "" : "none";
        return marker;
      });
      loadedRef.current = true;
    });

    return () => {
      map.remove();
      mapRef.current = null;
      loadedRef.current = false;
    };
  }, []);

  // Resource markers (hospitals/shelters/teams/ambulances)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !resources) return;
    resourceMarkersRef.current.forEach((m) => m.remove());
    resourceMarkersRef.current = [];
    (Object.entries(RESOURCE_COLORS) as [ResourceCategory, string][]).forEach(([category, color]) => {
      (resources[category] || []).forEach(
        (item) => {
          const marker = new Marker({ element: resourceMarkerEl(category, color) })
            .setLngLat([item.lon, item.lat])
            .setPopup(
              new Popup({ offset: 14 }).setText(
                `${category.slice(0, -1)}: ${item.name || item.id}`
              )
            )
            .addTo(map);
          resourceMarkersRef.current.push(marker);
        }
      );
    });
  }, [resources]);

  // Periodic pulse on a random data-source station — simulates a call just
  // landing, so the mock stations read as live without needing a real feed.
  useEffect(() => {
    const pulseId = setInterval(() => {
      const markers = dataSourceMarkersRef.current;
      if (markers.length === 0) return;
      const el = markers[Math.floor(Math.random() * markers.length)].getElement();
      el.classList.add("pulse-glow");
      setTimeout(() => el.classList.remove("pulse-glow"), 1200);
    }, 2500);
    return () => clearInterval(pulseId);
  }, []);

  // Data source layer visibility toggle
  useEffect(() => {
    dataSourceMarkersRef.current.forEach((m) => {
      m.getElement().style.display = layersVisible.dataSources ? "" : "none";
    });
  }, [layersVisible.dataSources]);

  // Incident pins (tracker 3.11.5 /map) — plots every known incident from
  // GET /incidents, not just ones with a live recommendation this session.
  // Selected pin uses the console-primary color, others a neutral outline
  // gray, matching the Kinetic Command palette.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !incidents) return;
    incidentMarkersRef.current.forEach((m) => m.remove());
    incidentMarkersRef.current = [];
    incidents.forEach((inc) => {
      if (inc.lat == null || inc.lon == null) return;
      const selected = inc.incident_id === selectedIncidentId;
      const marker = new Marker({ element: incidentMarkerEl(selected) })
        .setLngLat([inc.lon, inc.lat])
        .setPopup(
          new Popup({ offset: 14 }).setText(
            `${inc.incident_id}${inc.district ? ` — ${inc.district}` : ""}`
          )
        )
        .addTo(map);
      marker.getElement().style.cursor = "pointer";
      marker.getElement().addEventListener("click", () => onSelectIncident?.(inc.incident_id));
      incidentMarkersRef.current.push(marker);
    });
  }, [incidents, selectedIncidentId, onSelectIncident]);

  // Resource marker visibility toggle
  useEffect(() => {
    resourceMarkersRef.current.forEach((m) => {
      m.getElement().style.display = layersVisible.resources ? "" : "none";
    });
  }, [layersVisible.resources]);

  // Severity heat layer visibility + data
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    map.setLayoutProperty(
      "severity-fill",
      "visibility",
      layersVisible.severity ? "visible" : "none"
    );
  }, [layersVisible.severity]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current || !severityGeojson) return;
    (map.getSource("severity") as GeoJSONSource).setData(
      severityGeojson
    );
  }, [severityGeojson]);

  // Routes layer visibility + data (derived from AG-6 recommendations)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    map.setLayoutProperty(
      "routes-line",
      "visibility",
      layersVisible.routes ? "visible" : "none"
    );
  }, [layersVisible.routes]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    const routesByIncident: Record<
      string,
      { route_line: [number, number][]; blocked: boolean }
    > = {};
    recommendations.forEach((rec) => {
      if (rec.agent_id === "AG-6" && rec.details?.route_line) {
        routesByIncident[rec.incident_id] = {
          route_line: rec.details.route_line,
          blocked: !!rec.details.blocked,
        };
      }
    });
    const features = Object.entries(routesByIncident).map(
      ([incidentId, r]) => ({
        type: "Feature" as const,
        geometry: { type: "LineString" as const, coordinates: r.route_line },
        properties: { incident_id: incidentId, blocked: r.blocked },
      })
    );
    (map.getSource("routes") as GeoJSONSource).setData({
      type: "FeatureCollection",
      features,
    });
  }, [recommendations]);

  // Recommendation pins (new incident locations)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loadedRef.current) return;
    recommendations.forEach((rec) => {
      if (
        recMarkersRef.current.has(rec.rec_id) ||
        !rec.geo?.coordinates ||
        rec.geo.coordinates.length !== 2
      ) {
        return;
      }
      const marker = new Marker({ element: severityMarkerEl(rec.severity) })
        .setLngLat(rec.geo.coordinates)
        .setPopup(new Popup({ offset: 14 }).setText(rec.rationale))
        .addTo(map);
      recMarkersRef.current.set(rec.rec_id, marker);
    });
  }, [recommendations]);

  // MapLibre sets this element's inline `position` to "relative" itself,
  // overriding a Tailwind `absolute` class — so size it with h-full/w-full
  // instead of inset-0, which works regardless of the position value as long
  // as the parent (Dashboard's `relative h-screen` div) has a definite height.
  return <div ref={containerRef} className="absolute inset-0 h-full w-full" />;
}
