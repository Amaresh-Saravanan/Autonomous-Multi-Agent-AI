import type { IncidentState, Recommendation } from "./types";

export function relativeAge(epochSeconds: number): string {
  const mins = Math.max(0, Math.round((Date.now() / 1000 - epochSeconds) / 60));
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  return `${hrs}h ago`;
}

// AG-1..8 outputs live in the blackboard as one Recommendation per agent id,
// alongside a "conflicts" array (AC-4) — split them apart for display.
export function agentEntries(state: IncidentState | null): [string, Recommendation][] {
  if (!state) return [];
  return Object.entries(state).filter(
    (entry): entry is [string, Recommendation] => entry[0] !== "conflicts"
  );
}
