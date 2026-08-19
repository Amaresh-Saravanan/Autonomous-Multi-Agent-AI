"use client";

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

// Severity is never encoded by color alone (UX_DESIGN §6): icon + text label too.
const SEV_LABEL: Record<string, string> = {
  low: "◆ LOW",
  high: "▲ HIGH",
  critical: "⚠ CRITICAL",
};

export default function SituationPanel({ summary }: { summary?: Recommendation }) {
  if (!summary) {
    return <div className="text-xs text-[var(--text-muted)]">No incident activity yet.</div>;
  }
  const cls = sevClass(summary.severity);
  return (
    <div className="text-xs">
      <span
        className="mb-1.5 inline-block rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide"
        style={{ color: BORDER_COLOR[cls], border: `1px solid ${BORDER_COLOR[cls]}` }}
      >
        {SEV_LABEL[cls]}
      </span>
      <p className="text-[var(--text-muted)]">{summary.rationale}</p>
    </div>
  );
}
