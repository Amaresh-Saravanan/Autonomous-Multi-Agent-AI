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
    <div className="flex flex-col gap-2 pt-1">
      <label className="flex cursor-pointer items-center gap-2 font-console-body-compact text-console-body-compact text-console-on-surface-variant hover:text-console-on-surface">
        <input
          type="checkbox"
          checked={value.severity}
          onChange={toggle("severity")}
          className="accent-console-primary"
        />
        Severity heat layer
      </label>
      <label className="flex cursor-pointer items-center gap-2 font-console-body-compact text-console-body-compact text-console-on-surface-variant hover:text-console-on-surface">
        <input
          type="checkbox"
          checked={value.routes}
          onChange={toggle("routes")}
          className="accent-console-primary"
        />
        Routes
      </label>
      <label className="flex cursor-pointer items-center gap-2 font-console-body-compact text-console-body-compact text-console-on-surface-variant hover:text-console-on-surface">
        <input
          type="checkbox"
          checked={value.resources}
          onChange={toggle("resources")}
          className="accent-console-primary"
        />
        Resources
      </label>
    </div>
  );
}
