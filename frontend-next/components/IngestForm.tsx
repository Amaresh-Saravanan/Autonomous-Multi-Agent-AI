"use client";

import { useState, type FormEvent } from "react";
import { ingestWaterLevel } from "@/lib/api";
import type { Recommendation } from "@/lib/types";

export default function IngestForm({
  onIngested,
}: {
  onIngested: (incidentId: string, recs: Recommendation[]) => void;
}) {
  const [reading, setReading] = useState("5.5");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const body = await ingestWaterLevel(parseFloat(reading));
    onIngested(body.incident_id, body.recommendations);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="glass-panel absolute bottom-4 left-4 z-30 rounded-xl px-3 py-3 text-xs"
    >
      Simulate water-level reading:{" "}
      <input
        type="number"
        step="0.1"
        value={reading}
        onChange={(e) => setReading(e.target.value)}
        className="mr-2 w-20 rounded border border-[var(--border)] bg-white/5 px-1 text-[var(--text-primary)]"
      />
      <button
        type="submit"
        className="cursor-pointer rounded border border-[var(--border)] bg-white/5 px-2 py-1 hover:bg-white/12"
      >
        Send critical spike
      </button>
    </form>
  );
}
