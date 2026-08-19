"use client";

import type { ResourceCategory, ResourceItem, ResourcesResponse } from "@/lib/types";

const LABELS: Record<ResourceCategory, string> = {
  hospitals: "Hospitals",
  shelters: "Shelters",
  teams: "Teams",
  ambulances: "Ambulances",
};

function statusLine(category: ResourceCategory, item: ResourceItem): string {
  if (category === "hospitals") return `${item.free_beds}/${item.capacity} beds free`;
  if (category === "shelters") {
    const capacity = Number(item.capacity ?? 0);
    const occupied = Number(item.occupied ?? 0);
    return `${capacity - occupied}/${capacity} spaces free`;
  }
  return String(item.status ?? "");
}

const CATEGORIES: ResourceCategory[] = ["hospitals", "shelters", "teams", "ambulances"];

export default function ResourcesPanel({ resources }: { resources: ResourcesResponse | null }) {
  if (!resources) {
    return <div className="text-xs text-[var(--text-muted)]">Loading…</div>;
  }
  return (
    <div className="flex flex-col gap-2.5 text-xs">
      {CATEGORIES.map((cat) => (
        <div key={cat}>
          <div className="font-semibold text-[var(--text-primary)]">
            {LABELS[cat]} ({resources[cat].length})
          </div>
          {resources[cat].map((item) => (
            <div key={item.id} className="flex justify-between text-[var(--text-muted)]">
              <span>{String(item.name ?? item.id)}</span>
              <span>{statusLine(cat, item)}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
