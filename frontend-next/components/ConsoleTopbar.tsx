"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { useOperationsData } from "@/lib/operations-context";
import ThemeToggle from "./ThemeToggle";

function useClock() {
  const [now, setNow] = useState("");
  useEffect(() => {
    function tick() {
      setNow(new Date().toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
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
// single-page dashboard.
export default function ConsoleTopbar() {
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
    <div className="glass-panel flex items-center justify-between gap-3 border-b border-[var(--border)] px-4 py-2 text-xs">
      <div className="flex items-center gap-3 tracking-widest text-[var(--text-muted)] uppercase">
        <span
          className="h-1.5 w-1.5 rounded-full"
          style={{
            background: wsStatus === "live" ? "var(--sev-low)" : "var(--sev-moderate)",
            animation: "livePulse 2.4s ease-out infinite",
          }}
        />
        <strong className="font-bold text-[var(--text-primary)]">EOC</strong>
        Operations Console
        {criticalCount > 0 && (
          <span className="normal-case tracking-normal" style={{ color: "var(--sev-critical)" }}>
            ⚠ {criticalCount} critical
          </span>
        )}
        {highCount > 0 && (
          <span className="normal-case tracking-normal" style={{ color: "var(--sev-high)" }}>
            ▲ {highCount} high
          </span>
        )}
        <span className="normal-case tracking-normal" suppressHydrationWarning>
          {wsStatus}
        </span>
        <span className="normal-case tracking-normal" suppressHydrationWarning>
          {clock}
        </span>
      </div>
      <div className="flex items-center gap-2 text-[var(--text-muted)]">
        <ThemeToggle />
        {user && (
          <>
            <span>
              {user.username} ({user.role})
            </span>
            <button
              onClick={logout}
              className="cursor-pointer rounded border border-[var(--border)] bg-white/5 px-1.5 py-0.5 text-[var(--text-primary)] hover:bg-white/15"
            >
              Log out
            </button>
          </>
        )}
      </div>
    </div>
  );
}
