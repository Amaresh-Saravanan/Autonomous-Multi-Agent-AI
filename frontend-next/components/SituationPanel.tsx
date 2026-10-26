"use client";

import type { Recommendation } from "@/lib/types";
import SeverityBadge, { severityClass } from "./SeverityBadge";

export default function SituationPanel({ summary }: { summary?: Recommendation }) {
  if (!summary) {
    return (
      <div className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
        No incident activity yet.
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-console-sm pt-1">
      <div className="flex items-center gap-console-sm">
        <SeverityBadge level={severityClass(summary.severity)} />
        <span className="font-console-data-tabular text-[12px] text-console-on-surface-variant">
          {summary.severity.toFixed(2)}
        </span>
      </div>
      <p className="font-console-body-sm text-console-body-sm leading-relaxed text-console-on-surface-variant">
        {summary.rationale}
      </p>
    </div>
  );
}
