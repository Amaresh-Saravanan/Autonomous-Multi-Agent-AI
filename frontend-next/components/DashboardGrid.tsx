"use client";

import { useEffect, useState, type ReactNode } from "react";
import GridLayout, { useContainerWidth, type Layout } from "react-grid-layout";
import "react-grid-layout/css/styles.css";

// react-grid-layout v2: GridLayout needs an explicit pixel width (no built-in
// WidthProvider on the default export), so useContainerWidth measures the
// overlay wrapper. The grid floats over the pinned map — the wrapper is
// click-through (pointer-events:none, set in globals.css) and only the tiles
// capture pointer events, so the map stays draggable in the gaps.

const STORAGE_KEY = "dashboardLayout.v1";

// Per-role default layouts (PRD UI-5 / UX_DESIGN §3.1). Scoped to the three
// roles the RBAC actually has (admin/operator/viewer) rather than the
// finer-grained personas the UX doc sketches, since the backend has no such
// roles. operator = dispatch-focused (tall Alerts on top); viewer = monitor
// (tall Recommendations); admin = balanced.
// ponytail: one shared localStorage key across roles on a browser, so the
// last saved layout wins regardless of who's logged in — fine until there's
// real per-user server storage (deferred with the DB).
const ROLE_LAYOUTS: Record<string, Layout> = {
  admin: [
    { i: "layers", x: 0, y: 0, w: 2, h: 2 },
    { i: "situation", x: 0, y: 2, w: 3, h: 3 },
    { i: "resources", x: 0, y: 5, w: 3, h: 5 },
    { i: "citizen", x: 0, y: 10, w: 3, h: 4 },
    { i: "alerts", x: 9, y: 0, w: 3, h: 5 },
    { i: "recs", x: 9, y: 5, w: 3, h: 5 },
  ],
  operator: [
    { i: "layers", x: 0, y: 0, w: 2, h: 2 },
    { i: "situation", x: 0, y: 2, w: 3, h: 3 },
    { i: "resources", x: 0, y: 5, w: 3, h: 5 },
    { i: "citizen", x: 0, y: 10, w: 3, h: 4 },
    { i: "alerts", x: 9, y: 0, w: 3, h: 7 },
    { i: "recs", x: 9, y: 7, w: 3, h: 4 },
  ],
  viewer: [
    { i: "layers", x: 0, y: 0, w: 2, h: 2 },
    { i: "situation", x: 0, y: 2, w: 3, h: 3 },
    { i: "resources", x: 0, y: 5, w: 3, h: 5 },
    { i: "citizen", x: 0, y: 10, w: 3, h: 4 },
    { i: "alerts", x: 9, y: 0, w: 3, h: 4 },
    { i: "recs", x: 9, y: 4, w: 3, h: 7 },
  ],
};

function defaultForRole(role: string): Layout {
  return ROLE_LAYOUTS[role] ?? ROLE_LAYOUTS.admin;
}

function loadLayout(role: string): Layout {
  if (typeof window === "undefined") return defaultForRole(role);
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    /* fall through to the role default */
  }
  return defaultForRole(role);
}

export interface TileDef {
  key: string;
  title: string;
  content: ReactNode;
}

export default function DashboardGrid({
  tiles,
  editMode,
  role,
}: {
  tiles: TileDef[];
  editMode: boolean;
  role: string;
}) {
  const { width, containerRef, mounted } = useContainerWidth();
  const [layout, setLayout] = useState<Layout>(() => defaultForRole(role));

  useEffect(() => {
    setLayout(loadLayout(role));
  }, [role]);

  function persist(next: Layout) {
    setLayout(next);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      /* localStorage full/unavailable — layout just won't persist */
    }
  }

  return (
    <div
      ref={containerRef}
      className="pointer-events-none absolute inset-0 z-30"
    >
      {mounted && width > 0 && (
        <GridLayout
          width={width}
          layout={layout}
          onLayoutChange={persist}
          gridConfig={{ cols: 12, rowHeight: 72, margin: [12, 12] }}
          dragConfig={{ enabled: editMode, handle: ".tile-handle" }}
          resizeConfig={{ enabled: editMode, handles: ["se"] }}
        >
          {tiles.map((tile) => (
            <div key={tile.key} className="pointer-events-auto">
              <div
                className={`glass-panel flex h-full flex-col overflow-hidden ${
                  editMode ? "outline-2 outline-dashed outline-[var(--accent)]" : ""
                }`}
              >
                <div
                  className={`tile-handle flex items-center justify-between px-3 py-2 ${
                    editMode ? "cursor-move bg-white/5" : ""
                  }`}
                >
                  <span className="text-xs font-bold tracking-wider text-[var(--text-muted)] uppercase">
                    {tile.title}
                  </span>
                  {editMode && (
                    <span className="text-[var(--text-muted)]" aria-hidden>
                      ⠿
                    </span>
                  )}
                </div>
                <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
                  {tile.content}
                </div>
              </div>
            </div>
          ))}
        </GridLayout>
      )}
    </div>
  );
}
