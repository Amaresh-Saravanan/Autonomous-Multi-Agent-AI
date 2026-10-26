"use client";

import { AnimatePresence } from "framer-motion";
import RecCard from "./RecCard";
import type { Recommendation } from "@/lib/types";

export default function RecommendationsPanel({
  recommendations,
  onDecided,
}: {
  recommendations: Recommendation[];
  onDecided: (updated: Recommendation) => void;
}) {
  const sorted = [...recommendations].sort((a, b) =>
    b.created_at.localeCompare(a.created_at)
  );

  return (
    <div className="pt-1">
      <AnimatePresence initial={false}>
        {sorted.map((rec, i) => (
          <RecCard key={rec.rec_id} rec={rec} index={i} onDecided={onDecided} />
        ))}
      </AnimatePresence>
    </div>
  );
}
