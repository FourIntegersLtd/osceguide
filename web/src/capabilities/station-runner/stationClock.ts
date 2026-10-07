import type { AttemptBrief } from "@/capabilities/attempt-runner/api";

/**
 * The clock fields of a brief. `created_at`, `started_at` and `server_time` reach the generated
 * `AttemptBrief` once openapi.json is regenerated; until then they are declared here.
 */
export type BriefClock = Pick<AttemptBrief, "status"> & {
  created_at?: string;
  started_at?: string | null;
  server_time?: string;
};

function secondsBetween(from: string | null | undefined, to: string | undefined): number | undefined {
  if (!from || !to) return undefined;
  const start = Date.parse(from);
  const end = Date.parse(to);
  if (Number.isNaN(start) || Number.isNaN(end)) return undefined;
  return Math.max(0, Math.floor((end - start) / 1000));
}

/**
 * Seconds already used in a phase, by the server's clock: reading runs from the attempt's creation,
 * the consultation from its start (nothing used before it began). `undefined` means the server did
 * not say, and the timer falls back to counting from its own mount.
 */
export function phaseElapsedSeconds(brief: BriefClock | null, phase: "reading" | "consultation"): number | undefined {
  if (!brief) return undefined;
  if (phase === "reading") return secondsBetween(brief.created_at, brief.server_time);
  return brief.started_at ? secondsBetween(brief.started_at, brief.server_time) : 0;
}
