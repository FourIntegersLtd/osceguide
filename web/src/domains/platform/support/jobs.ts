/** The age of a running background task, and paging the queue past its first page. */

/** The oldest event of a task as the console reads it (`Job` from the generated types fits). */
export interface JobLike {
  id: number;
  status: string;
  events?: { type: string; at: string }[];
}

/** Mirrors STALLED_AFTER_SECONDS in health/service.py: three quiet minutes is a dead worker. */
export const STALLED_AFTER_MINUTES = 3;

/**
 * "Running for 14 min" for a task a worker holds, and whether it has run long
 * enough that the server will accept a cancel. Null when it is not running or
 * its start was not recorded.
 */
export function jobRunningLabel(
  job: JobLike,
  now: Date,
): { text: string; cancellable: boolean } | null {
  if (job.status !== "doing") return null;
  const started = [...(job.events ?? [])].reverse().find((event) => event.type === "started");
  if (!started) return null;
  const minutes = Math.max(0, Math.floor((now.getTime() - new Date(started.at).getTime()) / 60_000));
  const hours = Math.floor(minutes / 60);
  const text = hours > 0 ? `Running for ${hours} h ${minutes % 60} min` : `Running for ${minutes} min`;
  return { text, cancellable: minutes >= STALLED_AFTER_MINUTES };
}

/** The live first page followed by older pages already fetched, each task once. */
export function mergeOlderJobs<T extends { id: number }>(first: T[], older: T[]): T[] {
  const seen = new Set(first.map((entry) => entry.id));
  return [...first, ...older.filter((entry) => !seen.has(entry.id))];
}
