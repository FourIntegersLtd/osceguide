/**
 * Waiting for a just-ended debrief's summary to be written.
 *
 * The summary is written by a background job after the transcript arrives, so
 * for a minute or so after "End debrief" the history really is empty. The
 * screen asks again until the summary for that debrief attempt is listed,
 * rather than saying "No debriefs yet" until someone reloads.
 */
export async function waitForDebrief(
  newestAttemptIds: (signal: AbortSignal) => Promise<readonly string[]>,
  debriefAttemptId: string,
  { signal, intervalMs = 4000, timeoutMs = 180_000 }: { signal: AbortSignal; intervalMs?: number; timeoutMs?: number },
): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (!signal.aborted) {
    try {
      if ((await newestAttemptIds(signal)).includes(debriefAttemptId)) return true;
    } catch {
      // A failed poll is retried; the history's own load reports real failures.
    }
    if (signal.aborted || Date.now() + intervalMs > deadline) return false;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  return false;
}
