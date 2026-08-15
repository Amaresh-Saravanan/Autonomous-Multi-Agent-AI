"use client";

import { AnimatePresence } from "framer-motion";
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
      <AnimatePresence initial={false}>
        {alerts.map((rec, i) => (
          <RecCard key={rec.rec_id} rec={rec} index={i} onDecided={onDecided} />
        ))}
      </AnimatePresence>
    </div>
  );
}
