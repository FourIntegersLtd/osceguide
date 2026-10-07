export const MAX_WAIT_MS = 10 * 60 * 1000;

export type PendingOutcome = "ready" | "failed" | "expired" | "waiting";

/**
 * What a poll of a marking job says. A failed attempt is a failure, shown as one with a retry; only
 * a job that never settled within `MAX_WAIT_MS` is expired. The two used to share one silent exit.
 */
export function pendingOutcome(input: {
  resultCount: number;
  attemptStatus: string | null;
  elapsedMs: number;
}): PendingOutcome {
  if (input.resultCount > 0) return "ready";
  if (input.attemptStatus === "failed") return "failed";
  return input.elapsedMs >= MAX_WAIT_MS ? "expired" : "waiting";
}
