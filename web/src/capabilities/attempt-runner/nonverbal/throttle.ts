// Decides which video frames are worth analysing, and backs off on a slow device so the voice
// call is never starved. Pure: the caller passes the clock and the measured detection time.
const BASE_INTERVAL_MS = 250;
const SLOW_INTERVAL_MS = 500;
const SLOW_MEAN_MS = 60;
const WINDOW = 20;

export class FrameThrottle {
  intervalMs = BASE_INTERVAL_MS;
  private last = Number.NEGATIVE_INFINITY;
  private count = 0;
  private total = 0;

  /** True when enough time has passed since the last processed frame (and marks this one processed). */
  shouldProcess(nowMs: number): boolean {
    if (nowMs - this.last < this.intervalMs) return false;
    this.last = nowMs;
    return true;
  }

  /** Records how long one detection took; after 20 frames a slow mean widens the gap. */
  record(durationMs: number): void {
    if (this.count >= WINDOW) return;
    this.count += 1;
    this.total += durationMs;
    if (this.count === WINDOW && this.total / WINDOW > SLOW_MEAN_MS) this.intervalMs = SLOW_INTERVAL_MS;
  }
}
