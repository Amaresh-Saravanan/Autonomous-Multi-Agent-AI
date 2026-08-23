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
    return (
      <div className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
        No incident activity yet.
      </div>
    );
  }
  const cls = sevClass(summary.severity);
  return (
    <div>
      <span
        className="mb-1.5 inline-block rounded px-1.5 py-0.5 font-console-label-caps text-[9px] font-bold tracking-wide"
        style={{ color: BORDER_COLOR[cls], border: `1px solid ${BORDER_COLOR[cls]}` }}
      >
        {SEV_LABEL[cls]}
      </span>
      <p className="font-console-body-sm text-console-body-sm leading-relaxed text-console-on-surface-variant">
        {summary.rationale}
      </p>
    </div>
  );
}
