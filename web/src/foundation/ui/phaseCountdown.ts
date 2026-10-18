/**
 * The arithmetic behind a phase countdown whose truth is the server's.
 *
 * The server says how many seconds of the phase are used (measured on its own clock, so device skew
 * cancels out); the browser turns that into a wall-clock deadline once and measures every tick
 * against it. Nothing is added up tick by tick, so a throttled background tab cannot drift, and
 * nothing is stored, so a reload re-reads the server instead of the browser.
 */
export function phaseDeadline(durationSeconds: number, elapsedSeconds: number, nowMs: number): number {
  return nowMs + Math.max(durationSeconds - elapsedSeconds, 0) * 1000;
}

export function secondsLeft(deadlineMs: number, nowMs: number): number {
  return Math.max(0, Math.ceil((deadlineMs - nowMs) / 1000));
}
