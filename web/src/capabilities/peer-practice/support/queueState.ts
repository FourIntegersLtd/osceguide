import type { QueueStatus } from "../api";
/** Queue entries never return to waiting after a terminal update. */
export function latestQueueStatus(entryId: string | null, ...snapshots: (QueueStatus | null | undefined)[]): QueueStatus | null {
  const rank = (status: QueueStatus) => status.status === "matched" ? 2 : status.status === "waiting" ? 0 : 1;
  return snapshots.reduce<QueueStatus | null>((latest, candidate) => {
    if (!entryId || candidate?.entry_id !== entryId) return latest;
    return !latest || rank(candidate) >= rank(latest) ? candidate : latest;
  }, null);
}
