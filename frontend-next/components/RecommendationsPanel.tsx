"use client";

import RecCard from "./RecCard";
import type { Recommendation } from "@/lib/types";

export default function RecommendationsPanel({
  recommendations,
  wsStatus,
  onDecided,
}: {
  recommendations: Recommendation[];
  wsStatus: string;
  onDecided: (updated: Recommendation) => void;
}) {
  const sorted = [...recommendations].sort((a, b) =>
    b.created_at.localeCompare(a.created_at)
  );

  return (
    <div>
      <h2 className="mb-2.5 text-xs font-bold tracking-wider text-[var(--text-muted)] uppercase">
        Recommendations
      </h2>
      <div className="mb-3 text-xs text-[var(--text-muted)]">{wsStatus}</div>
      {sorted.map((rec) => (
        <RecCard key={rec.rec_id} rec={rec} onDecided={onDecided} />
      ))}
    </div>
  );
}
