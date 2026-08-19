"use client";

import type { CitizenReport } from "@/lib/types";

export default function CitizenInboxPanel({ reports }: { reports: CitizenReport[] }) {
  if (reports.length === 0) {
    return <div className="text-xs text-[var(--text-muted)]">No citizen reports yet.</div>;
  }
  return (
    <div className="flex flex-col gap-2 text-xs">
      {reports.map((r) => (
        <div
          key={r.event_id}
          className="rounded-lg px-2.5 py-2"
          style={{
            borderLeft: r.flagged_for_review
              ? "4px solid var(--sev-critical)"
              : "4px solid var(--border)",
            background: "rgba(28,34,48,0.6)",
          }}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="font-semibold">{r.reporter_id}</span>
            {r.flagged_for_review && (
              <span
                className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold tracking-wide"
                style={{ color: "var(--sev-critical)", border: "1px solid var(--sev-critical)" }}
              >
                ⚠ FLAGGED
              </span>
            )}
          </div>
          <p className="mt-1 text-[var(--text-muted)]">{r.message}</p>
          <div className="mt-1 text-[var(--text-muted)]">
            claimed severity {r.claimed_severity.toFixed(2)} · trust {r.confidence.toFixed(2)}
          </div>
        </div>
      ))}
    </div>
  );
}
