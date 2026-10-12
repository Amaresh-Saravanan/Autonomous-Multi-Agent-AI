"use client";

import { useState, type FormEvent } from "react";
import { ingestWaterLevel } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function IngestForm({
  onIngested,
}: {
  onIngested: (incidentId: string) => void;
}) {
  const { token, user } = useAuth();
  const [reading, setReading] = useState("5.5");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    // V2: the response only confirms acceptance (202) — recommendations
    // arrive later over the WS once the agent chain actually runs.
    setError(null);
    try {
      const body = await ingestWaterLevel(token, parseFloat(reading));
      onIngested(body.incident_id);
    } catch {
      setError("Demo sensor unavailable");
    }
  }

  // The demo sensor is a server-side operator+ tool (see /api/demo-ingest).
  if (!user || user.role === "viewer") return null;

  return (
    <form
      onSubmit={handleSubmit}
      className="absolute bottom-4 left-4 z-30 flex items-center gap-console-sm rounded-xl border border-console-primary/30 bg-console-surface/90 px-console-md py-console-sm font-console-body-compact text-console-body-compact text-console-on-surface-variant shadow-2xl backdrop-blur-xl"
    >
      Simulate water-level reading:{" "}
      <input
        type="number"
        step="0.1"
        value={reading}
        onChange={(e) => setReading(e.target.value)}
        className="w-20 rounded-md border border-console-outline-variant/50 bg-white/5 px-2 py-1 font-console-data-tabular text-console-data-tabular text-console-on-surface focus:border-console-primary focus:outline-none"
      />
      <button
        type="submit"
        className="cursor-pointer rounded-md bg-console-primary px-3 py-1 font-console-label-caps text-console-label-caps text-console-on-primary transition-colors hover:bg-console-primary-container"
      >
        Send critical spike
      </button>
      {error && <span className="text-console-error">{error}</span>}
    </form>
  );
}
