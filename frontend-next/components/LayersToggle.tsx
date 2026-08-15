"use client";

export interface LayersVisible {
  severity: boolean;
  routes: boolean;
  resources: boolean;
}

export default function LayersToggle({
  value,
  onChange,
}: {
  value: LayersVisible;
  onChange: (next: LayersVisible) => void;
}) {
  const toggle = (key: keyof LayersVisible) => (e: React.ChangeEvent<HTMLInputElement>) =>
    onChange({ ...value, [key]: e.target.checked });

  return (
    <div className="glass-panel absolute top-4 left-4 z-30 flex flex-col gap-1.5 rounded-xl px-3 py-2.5 text-xs">
      <label className="flex cursor-pointer items-center gap-1.5">
        <input type="checkbox" checked={value.severity} onChange={toggle("severity")} />
        Severity heat layer
      </label>
      <label className="flex cursor-pointer items-center gap-1.5">
        <input type="checkbox" checked={value.routes} onChange={toggle("routes")} />
        Routes
      </label>
      <label className="flex cursor-pointer items-center gap-1.5">
        <input type="checkbox" checked={value.resources} onChange={toggle("resources")} />
        Resources
      </label>
    </div>
  );
}
