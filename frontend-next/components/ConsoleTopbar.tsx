"use client";

import { useEffect, useState } from "react";
import { Bell, Menu, Wifi, User as UserIcon } from "lucide-react";
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

// Shared shell topbar (plan Phase M, UX_DESIGN §3.2): owns global liveness
// (WS state, critical/high counts, clock) plus user/theme controls -- merges
// what BrandBar.tsx and WhoAmI.tsx each used to own separately on the old
// single-page dashboard. Visual language: stitch_eoc_command_console/
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

  return (
    <header className="flex h-10 items-center justify-between border-b border-console-outline-variant/30 bg-console-surface/80 px-lg backdrop-blur-xl">
      <div className="flex items-center gap-md">
        <button
          onClick={onMenuClick}
          aria-label="Toggle navigation"
          className="flex items-center justify-center rounded-md p-unit text-console-on-surface-variant hover:bg-console-surface-bright/50 md:hidden"
        >
          <Menu className="h-[18px] w-[18px]" />
        </button>
        <span className="font-console-display-header text-console-display-header uppercase tracking-wider text-console-primary">
          EOC
        </span>
        <div className="flex items-center gap-sm border-l border-console-outline-variant/30 pl-md">
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{
              background: wsStatus === "live" ? "var(--sev-low)" : "var(--sev-moderate)",
              animation: "livePulse 2.4s ease-out infinite",
            }}
          />
          <span
            className="font-console-data-tabular text-console-data-tabular text-console-on-surface-variant"
            suppressHydrationWarning
          >
            {clock}
          </span>
        </div>
        {criticalCount > 0 && (
          <span
            className="hidden font-console-data-tabular text-console-data-tabular sm:inline"
            style={{ color: "var(--sev-critical)" }}
          >
            ⚠ {criticalCount} critical
          </span>
        )}
        {highCount > 0 && (
          <span
            className="hidden font-console-data-tabular text-console-data-tabular sm:inline"
            style={{ color: "var(--sev-high)" }}
          >
            ▲ {highCount} high
          </span>
        )}
        <span
          className="hidden font-console-data-tabular text-console-data-tabular text-console-on-surface-variant md:inline"
          suppressHydrationWarning
        >
          {wsStatus}
        </span>
      </div>
      <div className="flex items-center gap-sm">
        <button
          aria-label="notifications"
          className="flex items-center justify-center rounded-md p-unit text-console-on-surface-variant transition-colors hover:bg-console-surface-bright/50 active:scale-95"
        >
          <Bell className="h-[18px] w-[18px]" />
        </button>
        <button
          aria-label="connection status"
          className="flex items-center justify-center rounded-md p-unit text-console-on-surface-variant transition-colors hover:bg-console-surface-bright/50 active:scale-95"
        >
          <Wifi className="h-[18px] w-[18px]" />
        </button>
        <ThemeToggle />
        {user && (
          <>
            <span className="hidden font-console-body-sm text-console-body-sm text-console-on-surface-variant sm:inline">
              {user.username} ({user.role})
            </span>
            <div className="flex h-6 w-6 items-center justify-center overflow-hidden rounded-full border border-console-outline-variant/50 bg-console-surface-container-highest">
              <UserIcon className="h-[14px] w-[14px] text-console-on-surface-variant" />
            </div>
            <button
              onClick={logout}
              className="cursor-pointer rounded-md border border-console-outline-variant/30 bg-white/5 px-sm py-unit font-console-body-sm text-console-body-sm text-console-on-surface hover:bg-white/15"
            >
              Log out
            </button>
          </>
        )}
      </div>
    </header>
  );
}
