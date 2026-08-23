"use client";

import { useState } from "react";
import { useOperationsData } from "@/lib/operations-context";
import type { ResourceCategory, ResourceItem } from "@/lib/types";

const LABELS: Record<ResourceCategory, string> = {
  hospitals: "Hospitals",
  shelters: "Shelters",
  teams: "Teams",
  ambulances: "Ambulances",
};

const CATEGORIES: ResourceCategory[] = ["hospitals", "shelters", "teams", "ambulances"];

// Free-fraction for capacity alerts; categories without capacity data (teams,
// ambulances — status-only, no numeric field in resources.py) return null.
function freeFraction(category: ResourceCategory, item: ResourceItem): number | null {
  if (category === "hospitals") {
    const cap = Number(item.capacity ?? 0);
    return cap > 0 ? Number(item.free_beds ?? 0) / cap : null;
  }
  if (category === "shelters") {
    const cap = Number(item.capacity ?? 0);
    return cap > 0 ? (cap - Number(item.occupied ?? 0)) / cap : null;
  }
  return null;
}

function statusLine(category: ResourceCategory, item: ResourceItem): string {
  if (category === "hospitals") return `${item.free_beds}/${item.capacity} beds free`;
  if (category === "shelters") {
    const capacity = Number(item.capacity ?? 0);
    const occupied = Number(item.occupied ?? 0);
    return `${capacity - occupied}/${capacity} spaces free`;
  }
  return String(item.status ?? "");
}

// Capacity-first resources page (tracker 3.11.6.5, UX_DESIGN §3.3
// Resources): summary cards + category table + capacity alerts + supplies
// (BE-3). AG-5/AG-4 allocation recommendations aren't a separate resource
// field (they live per-incident in the blackboard, same gap noted for
// /medical in the tracker) — deferred, not built here.
export default function ResourcesPage() {
  const { resources } = useOperationsData();
  const [activeCategory, setActiveCategory] = useState<ResourceCategory>("hospitals");

  if (!resources) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="font-console-body-sm text-console-body-sm text-console-on-surface-variant">
          Loading…
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-console-lg">
      <h1 className="mb-console-md font-console-display-header text-console-display-header uppercase tracking-wider text-console-on-surface">
        Resources
      </h1>

      {/* Summary cards */}
      <div className="mb-console-lg grid grid-cols-2 gap-console-md md:grid-cols-4">
        {CATEGORIES.map((cat) => (
          <div
            key={cat}
            className="rounded-xl border border-console-outline-variant/40 bg-console-surface/80 p-console-md shadow-lg backdrop-blur-xl"
          >
            <div className="font-console-label-caps text-[10px] uppercase text-console-on-surface-variant">
              {LABELS[cat]}
            </div>
            <div className="mt-1 font-console-data-metric-lg text-console-data-metric-lg text-console-on-surface">
              {resources[cat].length}
            </div>
          </div>
        ))}
      </div>

      {resources.supplies && (
        <div className="mb-console-lg rounded-xl border border-console-outline-variant/40 bg-console-surface/80 p-console-md shadow-lg backdrop-blur-xl">
          <h2 className="mb-console-sm font-console-label-caps text-console-label-caps uppercase text-console-on-surface">
            Supplies
          </h2>
          <div className="flex gap-console-lg">
            {Object.entries(resources.supplies).map(([key, value]) => (
              <div key={key}>
                <div className="font-console-label-caps text-[10px] uppercase text-console-on-surface-variant">
                  {key.replace(/_/g, " ")}
                </div>
                <div className="font-console-data-tabular text-console-data-tabular text-console-on-surface">
                  {value.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Category tabs */}
      <div className="mb-console-md flex gap-1">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setActiveCategory(cat)}
            className={`rounded-md px-console-md py-console-sm font-console-label-caps text-console-label-caps uppercase transition-colors ${
              activeCategory === cat
                ? "bg-console-primary/20 text-console-primary"
                : "text-console-on-surface-variant hover:bg-console-surface-container/40"
            }`}
          >
            {LABELS[cat]}
          </button>
        ))}
      </div>

      <div className="overflow-hidden rounded-xl border border-console-outline-variant/40 bg-console-surface/80 shadow-lg backdrop-blur-xl">
        <table className="w-full">
          <thead>
            <tr className="border-b border-console-outline-variant/20 bg-console-surface-container-low/50">
              <th className="px-console-md py-console-sm text-left font-console-label-caps text-console-label-caps uppercase text-console-on-surface-variant">
                Name
              </th>
              <th className="px-console-md py-console-sm text-left font-console-label-caps text-console-label-caps uppercase text-console-on-surface-variant">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {resources[activeCategory].map((item) => {
              const frac = freeFraction(activeCategory, item);
              const lowCapacity = frac !== null && frac < 0.2;
              return (
                <tr
                  key={item.id}
                  className={`border-b border-console-outline-variant/10 last:border-0 ${
                    lowCapacity ? "bg-[var(--sev-critical)]/10" : ""
                  }`}
                >
                  <td className="px-console-md py-console-sm font-console-body-compact text-console-body-compact text-console-on-surface">
                    {String(item.name ?? item.id)}
                  </td>
                  <td
                    className={`px-console-md py-console-sm font-console-data-tabular text-console-data-tabular ${
                      lowCapacity ? "font-bold text-[var(--sev-critical)]" : "text-console-on-surface-variant"
                    }`}
                  >
                    {lowCapacity && "⚠ "}
                    {statusLine(activeCategory, item)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
