"use client";

import { useEffect, useState } from "react";

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

export default function BrandBar({
  criticalCount = 0,
  highCount = 0,
}: {
  criticalCount?: number;
  highCount?: number;
}) {
  const clock = useClock();
  return (
    <div className="glass-panel absolute top-4 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 rounded-full px-3.5 py-1.5 text-xs tracking-widest text-[var(--text-muted)] uppercase">
      <span
        className="h-1.5 w-1.5 rounded-full bg-[var(--sev-low)]"
        style={{ animation: "livePulse 2.4s ease-out infinite" }}
      />
      <strong className="font-bold text-[var(--text-primary)]">EOC</strong>
      Command Dashboard
      {criticalCount > 0 && (
        <span
          className="normal-case tracking-normal"
          style={{ color: "var(--sev-critical)" }}
        >
          ⚠ {criticalCount} critical
        </span>
      )}
      {highCount > 0 && (
        <span
          className="normal-case tracking-normal"
          style={{ color: "var(--sev-high)" }}
        >
          ▲ {highCount} high
        </span>
      )}
      <span className="normal-case tracking-normal text-[var(--text-muted)]" suppressHydrationWarning>
        {clock}
      </span>
    </div>
  );
}
