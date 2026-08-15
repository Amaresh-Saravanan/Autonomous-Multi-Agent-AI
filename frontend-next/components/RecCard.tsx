"use client";

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
  onDecided,
}: {
  rec: Recommendation;
  onDecided: (updated: Recommendation) => void;
}) {
  const { token } = useAuth();
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
    <div
      className="mb-2.5 rounded-lg px-3 py-2.5 transition-transform hover:-translate-x-0.5"
      style={{
        borderLeft: `4px solid ${BORDER_COLOR[cls]}`,
        background: "rgba(28,34,48,0.6)",
        animation:
          cls === "critical"
            ? "slideIn 200ms ease-out, criticalBreathe 2.6s ease-in-out infinite"
            : "slideIn 200ms ease-out",
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
    </div>
  );
}
