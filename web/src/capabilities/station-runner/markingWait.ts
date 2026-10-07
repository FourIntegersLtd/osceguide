/**
 * Waiting for a marking to be stored, for the tab that ended the consultation.
 *
 * Two sources tell the wait to look again: a timer that backs off to a slow
 * ceiling and never stops, and a wake-up (an `attempt` event on `/me/events`,
 * or the stream reconnecting). Either way the answer comes from re-reading the
 * stored result, so an event sent before the stream connected, or while an
 * API restart had dropped it, costs a delay rather than the feedback: the
 * next check finds the result anyway.
 *
 * It used to give up after ten polls (about three minutes); a marking that
 * took four left the modal saying "taking longer than usual" for good while
 * the feedback sat in the database. Being slow is now only a message.
 *
 * An attempt the scorer gave up on (`failed`) will never get a result, so each
 * check that finds no result also asks whether the attempt failed, and says so
 * instead of waiting for ever.
 */

export const SLOW_AFTER_MS = 3 * 60 * 1000;
const FIRST_DELAY_MS = 3_000;
const CEILING_MS = 30_000;

export interface MarkingWaitTimers {
  now: () => number;
  setTimeout: (run: () => void, ms: number) => unknown;
  clearTimeout: (handle: unknown) => void;
}

const browserTimers: MarkingWaitTimers = {
  now: () => Date.now(),
  setTimeout: (run, ms) => globalThis.setTimeout(run, ms),
  clearTimeout: (handle) => globalThis.clearTimeout(handle as ReturnType<typeof setTimeout>),
};

export interface MarkingWait {
  /** Check now: something said the marking may have changed. */
  wake: () => void;
  /** Stop for good: the modal closed. */
  stop: () => void;
}

/** The delay before check number `tries` (0-based): 3 s, 6 s, ... up to 30 s, then 30 s forever. */
export function delayBefore(tries: number): number {
  return Math.min(CEILING_MS, FIRST_DELAY_MS * (tries + 1));
}

/** A check that rejects (a 502 during a restart) has simply not found anything yet. */
async function orFalse(check: () => Promise<boolean>): Promise<boolean> {
  try {
    return await check();
  } catch {
    return false;
  }
}

export function watchMarking({
  isMarked,
  failure,
  onReady,
  onSlow,
  timers = browserTimers,
}: {
  /** Whether a result is stored. A rejection (a 502 during a restart) counts as "not yet". */
  isMarked: () => Promise<boolean>;
  /** Whether the attempt will never be marked, and what to do then. A rejection counts as "not yet". */
  failure?: { check: () => Promise<boolean>; onFailed: () => void };
  onReady: () => void;
  onSlow: () => void;
  timers?: MarkingWaitTimers;
}): MarkingWait {
  const startedAt = timers.now();
  let tries = 0;
  let stopped = false;
  let slow = false;
  let checking = false;
  let wokenWhileChecking = false;
  let timer: unknown = null;

  const schedule = () => {
    if (stopped) return;
    if (timer !== null) timers.clearTimeout(timer);
    timer = timers.setTimeout(() => {
      timer = null;
      void check();
    }, delayBefore(tries));
  };

  const check = async () => {
    if (stopped) return;
    if (checking) {
      wokenWhileChecking = true;
      return;
    }
    checking = true;
    const marked = await orFalse(isMarked);
    checking = false;
    if (stopped) return;
    if (marked) {
      stopped = true;
      if (timer !== null) timers.clearTimeout(timer);
      onReady();
      return;
    }
    if (failure) {
      const failed = await orFalse(failure.check);
      if (stopped) return;
      if (failed) {
        stopped = true;
        if (timer !== null) timers.clearTimeout(timer);
        failure.onFailed();
        return;
      }
    }
    tries += 1;
    if (!slow && timers.now() - startedAt >= SLOW_AFTER_MS) {
      slow = true;
      onSlow();
    }
    if (wokenWhileChecking) {
      wokenWhileChecking = false;
      void check();
      return;
    }
    schedule();
  };

  schedule();

  return {
    wake: () => void check(),
    stop: () => {
      stopped = true;
      if (timer !== null) timers.clearTimeout(timer);
      timer = null;
    },
  };
}
