"use client";

import type { ResourceCategory, ResourceItem, ResourcesResponse } from "@/lib/types";

const LABELS: Record<ResourceCategory, string> = {
  hospitals: "Hospitals",
  shelters: "Shelters",
  teams: "Teams",
  ambulances: "Ambulances",
};

const CATEGORIES: ResourceCategory[] = ["hospitals", "shelters", "teams", "ambulances"];

// free / total for the two capacity-style categories; null for status-style
// ones (teams, ambulances). Same fields the old text line read.
function capacityOf(category: ResourceCategory, item: ResourceItem): { free: number; total: number; unit: string } | null {
  if (category === "hospitals") {
    return { free: Number(item.free_beds ?? 0), total: Number(item.capacity ?? 0), unit: "beds" };
  }
  if (category === "shelters") {
    const total = Number(item.capacity ?? 0);
    return { free: total - Number(item.occupied ?? 0), total, unit: "spaces" };
  }
  return null;
}

// Low free capacity reads as worse. Thresholds map onto the severity colors.
function barColor(ratio: number): string {
  if (ratio <= 0.1) return "var(--sev-critical)";
  if (ratio <= 0.3) return "var(--sev-high)";
  return "var(--sev-low)";
}

export default function ResourcesPanel({ resources }: { resources: ResourcesResponse | null }) {
  if (!resources) {
    return (
      <div className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
        Loading…
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-console-lg pt-1">
      {CATEGORIES.map((cat) => (
        <div key={cat} className="flex flex-col gap-console-sm">
          <div className="font-console-label-caps text-[10px] font-semibold uppercase tracking-[0.12em] text-console-outline">
            {LABELS[cat]} ({resources[cat].length})
          </div>
          {resources[cat].map((item) => {
            const cap = capacityOf(cat, item);
            if (cap) {
              const ratio = cap.total > 0 ? Math.max(0, Math.min(1, cap.free / cap.total)) : 0;
              const color = barColor(ratio);
              return (
                <div key={item.id}>
                  <div className="mb-1 flex justify-between gap-2 font-console-body-sm text-console-body-sm">
                    <span className="truncate text-console-on-surface-variant">
                      {String(item.name ?? item.id)}
                    </span>
                    <span className="shrink-0 font-console-data-tabular text-[12px] text-console-on-surface">
                      {cap.free} / {cap.total} {cap.unit}
                    </span>
                  </div>
                  <div
                    role="meter"
                    aria-label={`${String(item.name ?? item.id)} free ${cap.unit}`}
                    aria-valuemin={0}
                    aria-valuemax={cap.total}
                    aria-valuenow={cap.free}
                    className="h-1 rounded-full bg-console-outline-variant/30"
                  >
                    <div
                      className="h-1 rounded-full"
                      style={{ width: `${ratio * 100}%`, background: color }}
                    />
                  </div>
                </div>
              );
            }
            const status = String(item.status ?? "");
            const ok = status === "available";
            return (
              <div
                key={item.id}
                className="flex justify-between gap-2 font-console-body-sm text-console-body-sm"
              >
                <span className="truncate text-console-on-surface-variant">
                  {String(item.name ?? item.id)}
                </span>
                <span
                  className="flex shrink-0 items-center gap-1.5 font-console-data-tabular text-[12px]"
                  style={{ color: ok ? "var(--sev-low)" : "var(--sev-moderate)" }}
                >
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: "currentColor" }} />
                  {status}
                </span>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
