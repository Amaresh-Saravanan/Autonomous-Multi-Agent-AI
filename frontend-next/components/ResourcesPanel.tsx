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
    return (
      <div className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
        Loading…
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-console-md">
      {CATEGORIES.map((cat) => (
        <div key={cat}>
          <div className="font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
            {LABELS[cat]} ({resources[cat].length})
          </div>
          {resources[cat].map((item) => (
            <div
              key={item.id}
              className="flex justify-between gap-2 font-console-body-sm text-console-body-sm text-console-on-surface-variant"
            >
              <span className="truncate">{String(item.name ?? item.id)}</span>
              <span className="shrink-0 font-console-data-tabular text-console-data-tabular text-console-on-surface">
                {statusLine(cat, item)}
              </span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
