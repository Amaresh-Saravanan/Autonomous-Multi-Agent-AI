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

// Severity is never encoded by color alone (accessibility, life-critical
// context — UX_DESIGN §6): each level carries an icon + a text label too.
const SEV_LABEL: Record<string, string> = {
  low: "◆ LOW",
  high: "▲ HIGH",
  critical: "⚠ CRITICAL",
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
  const { token, user } = useAuth();
  const reduce = useReducedMotion();
  const cls = sevClass(rec.severity);
  // Viewer role can read recommendations but not decide them (UX_DESIGN §3.4:
  // Recommendations = "Read" for viewer, "Approve/reject" for operator+) —
  // the backend already 403s viewer approve/reject calls; hiding the
  // buttons instead of showing an alert() on failure (tracker 3.11.7).
  const canDecide = user?.role !== "viewer";

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
      className={`mb-sm rounded-md border border-console-outline-variant/20 bg-console-surface-container/60 px-md py-sm ${
        cls === "critical" ? "pulse-glow" : ""
      }`}
      style={{ borderLeft: `4px solid ${BORDER_COLOR[cls]}` }}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="font-console-data-tabular text-console-data-tabular font-semibold tracking-wide text-console-on-surface">
          {rec.agent_id} · {rec.action}
        </div>
        <span
          className="shrink-0 rounded px-1.5 py-0.5 font-console-label-caps text-[9px] font-bold tracking-wide"
          style={{ color: BORDER_COLOR[cls], border: `1px solid ${BORDER_COLOR[cls]}` }}
        >
          {SEV_LABEL[cls]}
        </span>
      </div>
      <div className="mt-1 font-console-body-sm text-console-body-sm text-console-on-surface-variant">
        {rec.rationale}
      </div>
      <div className="mt-1 font-console-data-tabular text-[10px] text-console-outline">
        confidence {rec.confidence.toFixed(2)} · {rec.status}
      </div>
      {rec.status === "pending" && canDecide && (
        <div className="mt-sm flex gap-2">
          <button
            onClick={() => decide("approve")}
            className="flex-1 cursor-pointer rounded border border-console-primary/30 bg-console-primary/10 py-1 font-console-label-caps text-[10px] text-console-primary transition-colors hover:bg-console-primary/20"
          >
            APPROVE
          </button>
          <button
            onClick={() => decide("reject")}
            className="flex-1 cursor-pointer rounded border border-console-outline-variant/30 bg-console-surface py-1 font-console-label-caps text-[10px] text-console-on-surface-variant transition-colors hover:bg-console-surface-bright"
          >
            REJECT
          </button>
        </div>
      )}
      {rec.status === "pending" && !canDecide && (
        <div className="mt-sm font-console-label-caps text-[9px] uppercase text-console-outline">
          View only — operator approval required
        </div>
      )}
    </motion.div>
  );
}
