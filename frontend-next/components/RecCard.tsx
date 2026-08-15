"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useAuth } from "@/lib/auth-context";
import { decideRecommendation } from "@/lib/api";
import type { Recommendation } from "@/lib/types";

function sevClass(sev: number) {
  if (sev >= 0.85) return "critical";
  if (sev >= 0.5) return "high";
  return "low";
}

const BORDER_COLOR: Record<string, string> = {
  low: "var(--sev-low)",
  high: "var(--sev-high)",
  critical: "var(--sev-critical)",
};

export default function RecCard({
  rec,
  index = 0,
  onDecided,
}: {
  rec: Recommendation;
  index?: number;
  onDecided: (updated: Recommendation) => void;
}) {
  const { token } = useAuth();
  const reduce = useReducedMotion();
  const cls = sevClass(rec.severity);

  async function decide(action: "approve" | "reject") {
    try {
      const updated = await decideRecommendation(token, rec.rec_id, action);
      onDecided(updated);
    } catch {
      alert("Failed to update recommendation");
    }
  }

  return (
    <motion.div
      layout
      // Enter: slide-up 12px + fade, staggered ~40ms per item so a burst of
      // alerts reads as a sequence (UX_DESIGN §4.1/§4.2). Exit: slide right out
      // (a decided card leaving the pending feed). Reduced-motion → instant.
      initial={reduce ? { opacity: 0 } : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduce ? { opacity: 0 } : { opacity: 0, x: 40 }}
      transition={{ duration: 0.2, ease: "easeOut", delay: reduce ? 0 : index * 0.04 }}
      className={`mb-2.5 rounded-lg px-3 py-2.5 ${cls === "critical" ? "critical-glow" : ""}`}
      style={{
        borderLeft: `4px solid ${BORDER_COLOR[cls]}`,
        background: "rgba(28,34,48,0.6)",
      }}
    >
      <div className="text-sm font-semibold">
        {rec.agent_id} · {rec.action}
      </div>
      <div className="mt-1 text-xs text-[var(--text-muted)]">{rec.rationale}</div>
      <div className="mt-1 text-xs text-[var(--text-muted)]">
        confidence {rec.confidence.toFixed(2)} · {rec.status}
      </div>
      {rec.status === "pending" && (
        <div className="mt-2 flex gap-2">
          <button
            onClick={() => decide("approve")}
            className="cursor-pointer rounded-md border border-[var(--border)] bg-white/5 px-2.5 py-1 text-[11px] hover:bg-white/12"
          >
            Approve
          </button>
          <button
            onClick={() => decide("reject")}
            className="cursor-pointer rounded-md border border-[var(--border)] bg-white/5 px-2.5 py-1 text-[11px] hover:bg-white/12"
          >
            Reject
          </button>
        </div>
      )}
    </motion.div>
  );
}
