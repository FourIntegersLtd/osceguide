/**
 * Waiting for a marking to be stored, for the tab that ended the consultation.
 *
 * Nothing here polls. The wait reads the stored result once when it starts and once on each
 * wake-up (an `attempt` event on `/me/events`, or the stream reconnecting or the tab being shown
 * again, which the hook reports as `resync`). An event sent while no stream was open is therefore
 * not lost: the reconnect asks for a re-read.
 *
 * Being slow is only a message: one timer calls `onSlow` after `SLOW_AFTER_MS` and reads nothing.
 *
 * An attempt the scorer gave up on (`failed`) will never get a result. The server announces that
 * with the same `attempt` event, so each check that finds no result also asks whether the attempt
 * failed, and says so instead of waiting for ever.
 */

export const SLOW_AFTER_MS = 3 * 60 * 1000;

/**
 * Whether the attempt will never get a result without somebody acting: it failed outright, or
 * the scorer gave up after its retries. `marking_failed` is read by hand until schema.d.ts is
 * regenerated (R-5).
 */
export function markingWillNotArrive(attempt: { status: string; marking_failed?: boolean }): boolean {
  return attempt.status === "failed" || attempt.marking_failed === true;
}

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
  let stopped = false;
  let checking = false;
  let wokenWhileChecking = false;
  const slowTimer = timers.setTimeout(() => {
    if (!stopped) onSlow();
  }, SLOW_AFTER_MS);

  const finish = () => {
    stopped = true;
    timers.clearTimeout(slowTimer);
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
      finish();
      onReady();
      return;
    }
    if (failure) {
      const failed = await orFalse(failure.check);
      if (stopped) return;
      if (failed) {
        finish();
        failure.onFailed();
        return;
      }
    }
    if (wokenWhileChecking) {
      wokenWhileChecking = false;
      void check();
    }
  };

  void check();

  return {
    wake: () => void check(),
    stop: finish,
  };
}
