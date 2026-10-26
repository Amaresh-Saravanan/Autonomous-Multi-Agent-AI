// Severity legend for the command map. Colour is paired with a distinct shape
// per level (solid+halo, solid, ring, small dot) so it reads without colour.
export default function MapLegend() {
  return (
    <div
      aria-label="Map legend"
      className="pointer-events-none absolute bottom-[72px] left-1/2 z-30 flex h-[34px] -translate-x-1/2 items-center gap-console-lg rounded-full border border-console-outline-variant/40 bg-console-surface/90 px-console-lg font-console-body-sm text-[11px] text-console-on-surface-variant shadow-lg backdrop-blur-xl"
    >
      <span className="flex items-center gap-1.5">
        <span
          className="h-2.5 w-2.5 rounded-full"
          style={{ background: "var(--sev-critical)", boxShadow: "0 0 0 3px color-mix(in srgb, var(--sev-critical) 25%, transparent)" }}
        />
        Critical
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full" style={{ background: "var(--sev-high)" }} />
        High
      </span>
      <span className="flex items-center gap-1.5">
        <span
          className="h-2.5 w-2.5 rounded-full border-[2.5px]"
          style={{ borderColor: "var(--sev-moderate)" }}
        />
        Medium
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-2 w-2 rounded-full" style={{ background: "var(--sev-low)" }} />
        Low
      </span>
    </div>
  );
}
