/**
 * Waiting for a just-ended debrief's summary to be written.
 *
 * The summary is written by a background job after the transcript arrives, so
 * for a minute or so after "End debrief" the history really is empty. The
 * screen asks again until the summary for that debrief attempt is listed,
 * rather than saying "No debriefs yet" until someone reloads.
 */
/** A run of this many failed polls is a failure the caller must show. */
const MAX_FAILURES = 3;

export async function waitForDebrief(
  newestAttemptIds: (signal: AbortSignal) => Promise<readonly string[]>,
  debriefAttemptId: string,
  {
    signal,
    intervalMs = 4000,
    timeoutMs = 180_000,
  }: { signal: AbortSignal; intervalMs?: number; timeoutMs?: number },
): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  let failures = 0;
  while (!signal.aborted) {
    try {
      if ((await newestAttemptIds(signal)).includes(debriefAttemptId)) return true;
      failures = 0;
    } catch (cause) {
      // One failed poll is retried; a run of them is a failure the caller must show.
      failures += 1;
      if (failures >= MAX_FAILURES && !signal.aborted) throw cause;
    }
    if (signal.aborted || Date.now() + intervalMs > deadline) return false;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  return false;
}
