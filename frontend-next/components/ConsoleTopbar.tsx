"use client";

import { useEffect, useState } from "react";
import { Bell, LogOut, Menu, Radar, TriangleAlert, ArrowUp } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useOperationsData } from "@/lib/operations-context";
import ThemeToggle from "./ThemeToggle";

function useClock() {
  const [now, setNow] = useState("");
  useEffect(() => {
    function tick() {
      setNow(new Date().toLocaleTimeString(undefined, { hour12: false }));
    }
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

function initials(username: string): string {
  const name = username.split("@")[0] ?? username;
  const parts = name.split(/[._\-\s]+/).filter(Boolean);
  const letters = parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2);
  return letters.toUpperCase();
}

// Shared shell topbar (plan Phase M, UX_DESIGN §3.2): owns global liveness
// (WS state, critical/high counts, clock) plus user/theme controls -- merges
// what BrandBar.tsx and WhoAmI.tsx each used to own separately on the old
// single-page dashboard. Visual language: docs/design/stitch_eoc_command_console/
// kinetic_command (Kinetic Command design system).
export default function ConsoleTopbar({ onMenuClick }: { onMenuClick?: () => void } = {}) {
  const { user, logout } = useAuth();
  const { recommendations, wsStatus } = useOperationsData();
  const clock = useClock();

  const criticalCount = recommendations.filter(
    (r) => r.severity >= 0.85 && r.status === "pending"
  ).length;
  const highCount = recommendations.filter(
    (r) => r.severity >= 0.5 && r.severity < 0.85 && r.status === "pending"
  ).length;
  const unread = criticalCount + highCount;
  const live = wsStatus === "live";

  return (
    <header className="flex h-12 items-center justify-between border-b border-console-outline-variant/30 bg-console-surface/80 px-console-lg backdrop-blur-xl">
      <div className="flex items-center gap-console-md">
        <button
          onClick={onMenuClick}
          aria-label="Toggle navigation"
          className="flex items-center justify-center rounded-md p-unit text-console-on-surface-variant hover:bg-console-surface-bright/50 md:hidden"
        >
          <Menu className="h-[18px] w-[18px]" strokeWidth={1.75} />
        </button>
        <div className="flex items-center gap-console-sm">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-console-primary text-console-on-primary">
            <Radar className="h-[18px] w-[18px]" strokeWidth={2} aria-hidden />
          </div>
          <span className="font-console-display-header text-[15px] font-semibold tracking-[0.04em] text-console-on-surface">
            EOC
          </span>
        </div>
        <span
          className="font-console-data-tabular text-[12px] text-console-on-surface-variant"
          suppressHydrationWarning
        >
          {clock}
        </span>
        {criticalCount > 0 && (
          <span
            className="hidden items-center gap-1 font-console-data-tabular text-console-data-tabular sm:inline-flex"
            style={{ color: "var(--sev-critical)" }}
          >
            <TriangleAlert className="h-[14px] w-[14px]" strokeWidth={1.75} aria-hidden />
            {criticalCount} critical
          </span>
        )}
        {highCount > 0 && (
          <span
            className="hidden items-center gap-1 font-console-data-tabular text-console-data-tabular sm:inline-flex"
            style={{ color: "var(--sev-high)" }}
          >
            <ArrowUp className="h-[14px] w-[14px]" strokeWidth={1.75} aria-hidden />
            {highCount} high
          </span>
        )}
      </div>
      <div className="flex items-center gap-console-sm">
        <div
          role="status"
          className="flex h-7 items-center gap-2 rounded-full border px-3 font-console-label-caps text-[11px] font-semibold uppercase tracking-[0.08em]"
          style={{
            color: live ? "var(--sev-low)" : "var(--sev-moderate)",
            borderColor: live ? "var(--sev-low)" : "var(--sev-moderate)",
            background: `color-mix(in srgb, ${live ? "var(--sev-low)" : "var(--sev-moderate)"} 10%, transparent)`,
          }}
          suppressHydrationWarning
        >
          <span
            className="h-[7px] w-[7px] rounded-full"
            style={{
              background: "currentColor",
              animation: live ? "livePulse 2.4s ease-out infinite" : undefined,
            }}
          />
          {live ? "Live" : wsStatus}
        </div>
        <button
          aria-label={unread > 0 ? `Notifications, ${unread} pending` : "Notifications"}
          className="relative flex h-9 w-9 items-center justify-center rounded-lg text-console-on-surface-variant transition-colors hover:bg-console-surface-bright/50 active:scale-95"
        >
          <Bell className="h-[18px] w-[18px]" strokeWidth={1.75} />
          {unread > 0 && (
            <span
              className="absolute right-1 top-1 flex h-[14px] min-w-[14px] items-center justify-center rounded-full px-1 font-console-data-tabular text-[10px] font-semibold text-black"
              style={{ background: "var(--sev-critical)" }}
            >
              {unread}
            </span>
          )}
        </button>
        <ThemeToggle />
        {user && (
          <>
            <div className="mx-1 h-5 w-px bg-console-outline-variant/40" />
            <div className="flex items-center gap-console-md">
              <div
                aria-hidden
                className="flex h-7 w-7 items-center justify-center rounded-full border border-console-outline-variant/50 bg-console-surface-container-highest font-console-label-caps text-[11px] font-semibold text-console-on-surface-variant"
              >
                {initials(user.username)}
              </div>
              <div className="hidden flex-col leading-tight sm:flex">
                <span className="font-console-body-sm text-console-body-sm text-console-on-surface">
                  {user.username}
                </span>
                <span className="font-console-label-caps text-[9px] font-semibold uppercase tracking-[0.12em] text-console-primary">
                  {user.role}
                </span>
              </div>
            </div>
            <button
              onClick={logout}
              aria-label="Log out"
              title="Log out"
              className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-lg text-console-on-surface-variant transition-colors hover:bg-console-surface-bright/50 hover:text-console-on-surface active:scale-95"
            >
              <LogOut className="h-[18px] w-[18px]" strokeWidth={1.75} />
            </button>
          </>
        )}
      </div>
    </header>
  );
}
