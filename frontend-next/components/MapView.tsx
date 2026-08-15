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
import type { Recommendation, ResourcesResponse } from "@/lib/types";

// maplibre-gl builds its worker URL as `new URL("./maplibre-gl-worker.mjs",
// import.meta.url)` with a dynamically constructed filename, which bundlers
// (webpack, Turbopack) can't statically detect to copy into the build output
// — the worker 404s silently and every tile request just hangs forever with
// no error. Pointing it at a manually-copied static copy (public/) is
// maplibre-gl's own documented workaround for this.
setWorkerUrl("/maplibre-gl-worker.mjs");

const RESOURCE_COLORS: Record<string, string> = {
  hospitals: "#EF4444",
  shelters: "#3B82F6",
  teams: "#A855F7",
  ambulances: "#F97316",
};

interface MapViewProps {
  resources: ResourcesResponse | null;
  recommendations: Recommendation[];
  severityGeojson: GeoJSON.FeatureCollection | null;
  layersVisible: { severity: boolean; routes: boolean; resources: boolean };
}

// Deepens CARTO Dark Matter's default blacks/grays to match this dashboard's
// own token palette (--bg-base #0B0E14) instead of the stock basemap colors —
// ported as-is from the Phase B command-center map style.
function tuneBasemapPalette(map: MaplibreMap) {
  const style = map.getStyle();
  style.layers.forEach((layer) => {
    try {
      if (layer.type === "background") {
        map.setPaintProperty(layer.id, "background-color", "#0B0E14");
      } else if (layer.type === "fill" && layer.id === "water") {
        map.setPaintProperty(layer.id, "fill-color", "#0F1626");
      } else if (
        layer.type === "fill" &&
        (layer.id.includes("landuse") ||
          layer.id.includes("landcover") ||
          layer.id.includes("park"))
      ) {
        map.setPaintProperty(layer.id, "fill-color", "#101521");
      } else if (layer.type === "line" && layer.id.includes("road")) {
        map.setPaintProperty(layer.id, "line-color", "#232A3D");
      }
    } catch {
      // not every layer accepts the paint prop we tried
    }
  });
}

export default function MapView({
  resources,
  recommendations,
  severityGeojson,
  layersVisible,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MaplibreMap | null>(null);
  const loadedRef = useRef(false);
  const resourceMarkersRef = useRef<Marker[]>([]);
  const recMarkersRef = useRef<Map<string, Marker>>(new Map());

  useEffect(() => {
    if (!containerRef.current) return;
    const map = new MaplibreMap({
      container: containerRef.current,
      style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
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
    Object.entries(RESOURCE_COLORS).forEach(([category, color]) => {
      (resources[category as keyof ResourcesResponse] || []).forEach(
        (item) => {
          const marker = new Marker({ color })
            .setLngLat([item.lon, item.lat])
            .setPopup(
              new Popup().setText(
                `${category.slice(0, -1)}: ${item.name || item.id}`
              )
            )
            .addTo(map);
          resourceMarkersRef.current.push(marker);
        }
      );
    });
  }, [resources]);

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
      const marker = new Marker({
        color: rec.severity >= 0.85 ? "#EF4444" : "#F97316",
      })
        .setLngLat(rec.geo.coordinates)
        .setPopup(new Popup().setText(rec.rationale))
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
