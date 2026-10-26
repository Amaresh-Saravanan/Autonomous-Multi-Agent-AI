"use client";

import { useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { useAuth } from "@/lib/auth-context";
import { decideRecommendation } from "@/lib/api";
import type { Recommendation } from "@/lib/types";
import SeverityBadge, { SEVERITY_COLOR, severityClass } from "./SeverityBadge";

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
  const [error, setError] = useState<string | null>(null);
  const cls = severityClass(rec.severity);
  // Viewer role can read recommendations but not decide them (UX_DESIGN §3.4:
  // Recommendations = "Read" for viewer, "Approve/reject" for operator+) —
  // the backend already 403s viewer approve/reject calls; hiding the
  // buttons instead of showing an alert() on failure (tracker 3.11.7).
  const canDecide = user?.role !== "viewer";
  const confidencePct = Math.max(0, Math.min(1, rec.confidence)) * 100;

  async function decide(action: "approve" | "reject") {
    setError(null);
    try {
      const updated = await decideRecommendation(token, rec.rec_id, action);
      onDecided(updated);
    } catch {
      setError("Couldn't save that decision — it may already be decided, or you lack permission.");
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
      className={`mb-console-sm rounded-lg border border-console-outline-variant/20 bg-console-surface-container/60 px-console-md py-console-md ${
        cls === "critical" ? "pulse-glow" : ""
      }`}
      style={{ borderLeft: `3px solid ${SEVERITY_COLOR[cls]}` }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-console-data-tabular text-[11px] font-semibold text-console-primary">
          {rec.agent_id}
        </span>
        <SeverityBadge level={cls} />
      </div>
      <div className="mt-1.5 font-console-body-compact text-[14px] font-semibold leading-snug text-console-on-surface">
        {rec.action}
      </div>

      <div className="mt-console-sm flex items-center gap-console-sm">
        <span className="font-console-label-caps text-[9px] font-semibold uppercase tracking-[0.12em] text-console-outline">
          Confidence
        </span>
        <div className="h-1 flex-1 rounded-full bg-console-outline-variant/30">
          <div
            className="h-1 rounded-full bg-console-primary"
            style={{ width: `${confidencePct}%` }}
          />
        </div>
        <span className="font-console-data-tabular text-[11px] text-console-on-surface-variant">
          {rec.confidence.toFixed(2)}
        </span>
      </div>

      {/* Rationale and evidence are always shown — every recommendation must
          be explainable. */}
      <div className="mt-console-md font-console-label-caps text-[9px] font-semibold uppercase tracking-[0.12em] text-console-outline">
        Rationale
      </div>
      <div className="mt-0.5 font-console-body-sm text-console-body-sm leading-relaxed text-console-on-surface-variant">
        {rec.rationale}
      </div>
      {rec.evidence.length > 0 && (
        <div className="mt-console-sm flex flex-wrap items-center gap-1">
          <span className="font-console-label-caps text-[9px] font-semibold uppercase tracking-[0.12em] text-console-outline">
            Evidence
          </span>
          {rec.evidence.map((eventId) => (
            <span
              key={eventId}
              title={eventId}
              className="rounded border border-console-outline-variant/30 bg-console-surface px-1.5 py-0.5 font-console-data-tabular text-[10px] text-console-on-surface-variant"
            >
              {eventId.slice(0, 8)}
            </span>
          ))}
        </div>
      )}
      <div className="mt-console-sm font-console-data-tabular text-[10px] uppercase tracking-wide text-console-outline">
        {rec.status}
      </div>

      {rec.status === "pending" && canDecide && (
        <div className="mt-console-md flex gap-2">
          <button
            onClick={() => decide("approve")}
            className="h-8 flex-1 cursor-pointer rounded-md bg-console-primary font-console-body-sm text-[12px] font-semibold text-console-on-primary transition-colors hover:bg-console-primary-container"
          >
            Approve
          </button>
          <button
            onClick={() => decide("reject")}
            className="h-8 flex-1 cursor-pointer rounded-md border border-console-outline-variant/60 bg-transparent font-console-body-sm text-[12px] font-semibold text-console-on-surface transition-colors hover:bg-console-surface-bright"
          >
            Reject
          </button>
        </div>
      )}
      {error && (
        <div role="alert" className="mt-console-sm text-[11px] text-[var(--sev-critical)]">
          {error}
        </div>
      )}
      {rec.status === "pending" && !canDecide && (
        <div className="mt-console-sm font-console-label-caps text-[9px] uppercase tracking-[0.12em] text-console-outline">
          View only — operator approval required
        </div>
      )}
    </motion.div>
  );
}
