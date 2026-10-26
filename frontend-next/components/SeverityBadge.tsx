import { ArrowUp, Circle, TriangleAlert } from "lucide-react";

export type SeverityClass = "critical" | "high" | "low";

export function severityClass(sev: number): SeverityClass {
  if (sev >= 0.85) return "critical";
  if (sev >= 0.5) return "high";
  return "low";
}

export const SEVERITY_COLOR: Record<SeverityClass, string> = {
  low: "var(--sev-low)",
  high: "var(--sev-high)",
  critical: "var(--sev-critical)",
};

const LABEL: Record<SeverityClass, string> = {
  low: "Low",
  high: "High",
  critical: "Critical",
};

// Severity is never encoded by color alone (UX_DESIGN §6): each level carries
// its own icon shape plus a text label.
export default function SeverityBadge({ level }: { level: SeverityClass }) {
  const color = SEVERITY_COLOR[level];
  const Icon = level === "critical" ? TriangleAlert : level === "high" ? ArrowUp : Circle;
  return (
    <span
      className="inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 font-console-label-caps text-[10px] font-semibold uppercase tracking-[0.1em]"
      style={{
        color,
        borderColor: `color-mix(in srgb, ${color} 45%, transparent)`,
        background: `color-mix(in srgb, ${color} 14%, transparent)`,
      }}
    >
      <Icon className="h-[11px] w-[11px]" strokeWidth={2} aria-hidden />
      {LABEL[level]}
    </span>
  );
}
