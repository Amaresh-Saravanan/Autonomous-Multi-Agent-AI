"use client";

import { AnimatePresence } from "framer-motion";
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
      <div className="mb-3 text-xs text-[var(--text-muted)]">{wsStatus}</div>
      <AnimatePresence initial={false}>
        {sorted.map((rec, i) => (
          <RecCard key={rec.rec_id} rec={rec} index={i} onDecided={onDecided} />
        ))}
      </AnimatePresence>
    </div>
  );
}
