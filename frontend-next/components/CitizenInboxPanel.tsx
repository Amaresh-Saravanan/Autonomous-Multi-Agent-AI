"use client";

import type { CitizenReport } from "@/lib/types";

export default function CitizenInboxPanel({ reports }: { reports: CitizenReport[] }) {
  if (reports.length === 0) {
    return (
      <div className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
        No citizen reports yet.
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {reports.map((r) => (
        <div
          key={r.event_id}
          className="rounded-md border border-console-outline-variant/20 bg-console-surface-container/40 px-console-md py-console-sm"
          style={{
            borderLeft: r.flagged_for_review
              ? "4px solid var(--sev-critical)"
              : "4px solid var(--color-console-outline-variant)",
          }}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-console-data-tabular text-console-data-tabular text-console-on-surface">
              {r.reporter_id}
            </span>
            {r.flagged_for_review && (
              <span
                className="shrink-0 rounded px-1.5 py-0.5 font-console-label-caps text-[9px] font-bold tracking-wide"
                style={{ color: "var(--sev-critical)", border: "1px solid var(--sev-critical)" }}
              >
                ⚠ FLAGGED
              </span>
            )}
          </div>
          <p className="mt-1 font-console-body-sm text-console-body-sm text-console-on-surface-variant">
            {r.message}
          </p>
          <div className="mt-1 font-console-data-tabular text-[10px] text-console-outline">
            claimed severity {r.claimed_severity.toFixed(2)} · trust {r.confidence.toFixed(2)}
          </div>
        </div>
      ))}
    </div>
  );
}
