import type { AttemptBrief } from "@/capabilities/attempt-runner/api";

/** The clock fields of a brief, all from the generated `AttemptBrief`. */
export type BriefClock = Pick<AttemptBrief, "status" | "created_at" | "started_at" | "server_time">;

function secondsBetween(from: string | null | undefined, to: string | undefined): number {
  if (!from || !to) return 0;
  const start = Date.parse(from);
  const end = Date.parse(to);
  if (Number.isNaN(start) || Number.isNaN(end)) return 0;
  return Math.max(0, Math.floor((end - start) / 1000));
}

/**
 * Seconds already used in a phase, by the server's clock: reading runs from the attempt's creation,
 * the consultation from its start (nothing used before it began). True as of the brief's
 * `server_time`; the timer ages it from when the brief arrived. A server that did not say gives 0:
 * the whole phase is left, counted from when the brief arrived.
 */
export function phaseElapsedSeconds(brief: BriefClock | null, phase: "reading" | "consultation"): number {
  if (!brief) return 0;
  if (phase === "reading") return secondsBetween(brief.created_at, brief.server_time);
  return brief.started_at ? secondsBetween(brief.started_at, brief.server_time) : 0;
}
