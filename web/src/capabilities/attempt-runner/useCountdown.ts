"use client";

import { useEffect, useRef, useState } from "react";

/**
 * A countdown that survives a sleeping tab.
 *
 * Deadline-based rather than decrementing a number each tick: a background tab
 * throttles timers to once a minute, so a counter that subtracts one per tick
 * drifts minutes off over a station. The old clients had four such timers and
 * none of them agreed after a tab switch.
 *
 * It is still the browser's clock. Server-owned phases are the real fix and
 * the backend already carries the columns for them; this reads
 * `phase_ends_at` when a caller supplies one.
 */
export function useCountdown(
  totalSeconds: number,
  running: boolean,
  onElapsed?: () => void,
): { secondsLeft: number; elapsed: boolean } {
  const [secondsLeft, setSecondsLeft] = useState(totalSeconds);
  const deadlineRef = useRef<number | null>(null);
  const firedRef = useRef(false);
  const onElapsedRef = useRef(onElapsed);
  onElapsedRef.current = onElapsed;

  useEffect(() => {
    if (!running) {
      deadlineRef.current = null;
      firedRef.current = false;
      setSecondsLeft(totalSeconds);
      return;
    }

    deadlineRef.current ??= Date.now() + totalSeconds * 1000;

    const tick = () => {
      const deadline = deadlineRef.current;
      if (deadline === null) return;
      const left = Math.max(0, Math.round((deadline - Date.now()) / 1000));
      setSecondsLeft(left);
      if (left === 0 && !firedRef.current) {
        firedRef.current = true;
        onElapsedRef.current?.();
      }
    };

    tick();
    const id = window.setInterval(tick, 1000);
    // A tab coming back to the foreground re-reads the deadline immediately
    // rather than waiting for the next interval.
    const onVisible = () => {
      if (document.visibilityState === "visible") tick();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [running, totalSeconds]);

  return { secondsLeft, elapsed: secondsLeft === 0 };
}

export function formatClock(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(safe / 60);
  return `${minutes}:${String(safe % 60).padStart(2, "0")}`;
}
