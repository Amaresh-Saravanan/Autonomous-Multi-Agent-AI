export default function BrandBar() {
  return (
    <div className="glass-panel absolute top-4 left-1/2 -translate-x-1/2 z-40 flex items-center gap-2 rounded-full px-3.5 py-1.5 text-xs tracking-widest text-[var(--text-muted)] uppercase">
      <span
        className="h-1.5 w-1.5 rounded-full bg-[var(--sev-low)]"
        style={{ animation: "livePulse 2.4s ease-out infinite" }}
      />
      <strong className="font-bold text-[var(--text-primary)]">EOC</strong>
      Command Dashboard
    </div>
  );
}
