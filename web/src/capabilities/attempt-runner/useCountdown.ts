"use client";

import { useEffect, useRef, useState } from "react";
import {
  anchoredPhaseDeadline,
  secondsUntilPhaseDeadline,
  type ServerCountdownAnchor,
} from "@/foundation/ui/phaseCountdown";

export type CountdownAnchor = ServerCountdownAnchor;

/** The device time at which `totalSeconds` from the server's start runs out. */
export function anchoredDeadline(totalSeconds: number, anchor: CountdownAnchor): number {
  return anchoredPhaseDeadline(totalSeconds, anchor);
}

export function secondsUntil(deadlineMs: number, nowMs: number): number {
  return secondsUntilPhaseDeadline(deadlineMs, nowMs);
}

/** The anchor a brief gives, or `undefined` while the server has not started the phase. */
export function countdownAnchor(
  brief: { started_at?: string | null; server_time?: string },
  receivedAtMs: number,
): CountdownAnchor | undefined {
  const startedAtMs = brief.started_at ? Date.parse(brief.started_at) : NaN;
  const serverNowMs = brief.server_time ? Date.parse(brief.server_time) : NaN;
  if (Number.isNaN(startedAtMs) || Number.isNaN(serverNowMs)) return undefined;
  return { startedAtMs, serverOffsetMs: serverNowMs - receivedAtMs };
}

/**
 * A countdown that survives a sleeping tab.
 *
 * Deadline-based rather than decrementing a number each tick: a background tab
 * throttles timers to once a minute, so a counter that subtracts one per tick
 * drifts minutes off over a station. The old clients had four such timers and
 * none of them agreed after a tab switch.
 *
 * Without an `anchor` it is the browser's clock, started when the hook runs. With one (the
 * server's `started_at` and its offset from this device) the deadline is the server's, so a
 * reload or a late-joining screen shows what is really left.
 */
export function useCountdown(
  totalSeconds: number,
  running: boolean,
  onElapsed?: () => void,
  anchor?: CountdownAnchor,
): { secondsLeft: number; elapsed: boolean } {
  const [secondsLeft, setSecondsLeft] = useState(totalSeconds);
  const deadlineRef = useRef<number | null>(null);
  const firedRef = useRef(false);
  const onElapsedRef = useRef(onElapsed);
  onElapsedRef.current = onElapsed;
  const anchoredStart = anchor?.startedAtMs;
  const anchoredOffset = anchor?.serverOffsetMs;

  useEffect(() => {
    if (!running) {
      deadlineRef.current = null;
      firedRef.current = false;
      setSecondsLeft(totalSeconds);
      return;
    }

    if (anchoredStart !== undefined && anchoredOffset !== undefined) {
      deadlineRef.current = anchoredDeadline(totalSeconds, {
        startedAtMs: anchoredStart,
        serverOffsetMs: anchoredOffset,
      });
    } else {
      deadlineRef.current ??= Date.now() + totalSeconds * 1000;
    }

    const tick = () => {
      const deadline = deadlineRef.current;
      if (deadline === null) return;
      const left = secondsUntil(deadline, Date.now());
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
  }, [running, totalSeconds, anchoredStart, anchoredOffset]);

  return { secondsLeft, elapsed: secondsLeft === 0 };
}

export function formatClock(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(safe / 60);
  return `${minutes}:${String(safe % 60).padStart(2, "0")}`;
}
