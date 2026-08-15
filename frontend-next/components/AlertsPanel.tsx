"use client";

import RecCard from "./RecCard";
import type { Recommendation } from "@/lib/types";

export default function AlertsPanel({
  recommendations,
  onDecided,
}: {
  recommendations: Recommendation[];
  onDecided: (updated: Recommendation) => void;
}) {
  const alerts = recommendations
    .filter((r) => r.severity >= 0.5 && r.status === "pending")
    .sort((a, b) => b.created_at.localeCompare(a.created_at));

  return (
    <div>
      <h2 className="mb-2.5 text-xs font-bold tracking-wider text-[var(--text-muted)] uppercase">
        Alerts
      </h2>
      {alerts.map((rec) => (
        <RecCard key={rec.rec_id} rec={rec} onDecided={onDecided} />
      ))}
    </div>
  );
}
