"use client";

import { useEffect, useRef, useState } from "react";
import {
  MOCK_STATIONS,
  SOURCE_COLORS,
  SOURCE_ENDPOINTS,
  SOURCE_LABELS,
  nextMockEvent,
  type MockEvent,
  type SourceType,
} from "@/lib/mock-data-sources";

const SOURCE_TYPES: SourceType[] = ["iot", "weather", "satellite", "citizen"];
const FEED_LIMIT = 20;
const TICK_MS = 2200;

// Live "data sources" view for presentations (tracker: no backend endpoint
// lists ingestion devices or replays received events yet — see
// lib/mock-data-sources.ts). Simulates each ingestion endpoint receiving
// events on an interval so it reads like a real feed hitting
// POST /api/v1/ingestion/*.
export default function DataSourcesPage() {
  const [feed, setFeed] = useState<MockEvent[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    timerRef.current = setInterval(() => {
      setFeed((prev) => [nextMockEvent(), ...prev].slice(0, FEED_LIMIT));
    }, TICK_MS);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  return (
    <div className="h-full overflow-y-auto p-console-lg">
      <h1 className="mb-console-md font-console-display-header text-console-display-header uppercase tracking-wider text-console-on-surface">
        Data Sources
      </h1>
      <p className="mb-console-md font-console-body-sm text-console-body-sm text-console-on-surface-variant">
        Live ingestion feed across all device-authenticated sources. Demo data — not connected to real sensors.
      </p>

      <div className="grid grid-cols-1 gap-console-md md:grid-cols-2 lg:grid-cols-4">
        {SOURCE_TYPES.map((type) => {
          const latest = feed.find((e) => e.station.source_type === type);
          const count = feed.filter((e) => e.station.source_type === type).length;
          return (
            <div
              key={type}
              className="rounded-xl border border-console-outline-variant/40 bg-console-surface/80 p-console-md shadow-lg backdrop-blur-xl"
            >
              <div className="flex items-center justify-between">
                <span
                  className="font-console-data-tabular text-console-data-tabular font-semibold"
                  style={{ color: SOURCE_COLORS[type] }}
                >
                  {SOURCE_LABELS[type]}
                </span>
                <span className="flex items-center gap-1 font-console-label-caps text-[9px] font-bold uppercase text-[var(--sev-low)]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[var(--sev-low)] pulse-glow" />
                  Listening
                </span>
              </div>
              <div className="mt-1 font-console-data-tabular text-[10px] text-console-outline">
                POST {SOURCE_ENDPOINTS[type]}
              </div>
              {latest ? (
                <>
                  <p className="mt-2 font-console-body-sm text-[11px] text-console-on-surface-variant">
                    {latest.station.label}
                  </p>
                  <p className="mt-1 font-console-data-tabular text-[10px] text-console-outline">
                    {latest.latency_ms}ms · {new Date(latest.timestamp).toLocaleTimeString()}
                  </p>
                </>
              ) : (
                <p className="mt-2 font-console-body-sm text-[11px] text-console-outline">Waiting for first event…</p>
              )}
              <p className="mt-2 font-console-data-tabular text-[10px] text-console-outline">
                {count} received this session
              </p>
            </div>
          );
        })}
      </div>

      <h2 className="mb-console-sm mt-console-lg font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
        Live Feed
      </h2>
      <div className="overflow-hidden rounded-xl border border-console-outline-variant/40 bg-console-surface/80 shadow-lg backdrop-blur-xl">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-console-outline-variant/20 bg-console-surface-container-low/50">
              {["Time", "Source", "Device", "Payload", "Latency", "Status"].map((h) => (
                <th
                  key={h}
                  className="px-console-sm py-console-sm font-console-label-caps text-[9px] uppercase text-console-on-surface-variant"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {feed.map((e) => (
              <tr key={e.id} className="border-b border-console-outline-variant/10 last:border-0">
                <td className="px-console-sm py-1.5 font-console-data-tabular text-[10px] text-console-outline">
                  {new Date(e.timestamp).toLocaleTimeString()}
                </td>
                <td className="px-console-sm py-1.5 font-console-data-tabular text-[10px]" style={{ color: SOURCE_COLORS[e.station.source_type] }}>
                  {SOURCE_LABELS[e.station.source_type]}
                </td>
                <td className="px-console-sm py-1.5 font-console-data-tabular text-[10px] text-console-on-surface-variant">
                  {e.station.id}
                </td>
                <td className="px-console-sm py-1.5 font-console-data-tabular text-[10px] text-console-on-surface-variant">
                  {JSON.stringify(e.payload)}
                </td>
                <td className="px-console-sm py-1.5 font-console-data-tabular text-[10px] text-console-outline">
                  {e.latency_ms}ms
                </td>
                <td className="px-console-sm py-1.5 font-console-data-tabular text-[10px] text-[var(--sev-low)]">202 Accepted</td>
              </tr>
            ))}
            {feed.length === 0 && (
              <tr>
                <td colSpan={6} className="px-console-sm py-console-md text-center font-console-body-sm text-[11px] text-console-on-surface-variant">
                  Waiting for first event…
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="mt-console-sm font-console-data-tabular text-[10px] text-console-outline">
        {MOCK_STATIONS.length} stations configured — see Map for locations.
      </p>
    </div>
  );
}
