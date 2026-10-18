"use client";

import { useState, useEffect, useRef } from "react";
import { FiRotateCcw } from "react-icons/fi";

import ConfirmModal from "@/foundation/ui/ConfirmModal";
import { useToast } from "@/foundation/hooks/useToast";
import { phaseDeadline, secondsLeft } from "@/foundation/ui/phaseCountdown";

interface TimerProps {
  /** Length of this phase in seconds, as the caller derived it (custom timers included). */
  duration: number;
  /** Identifies the attempt, so its warning toast is not confused with another's. */
  stationId: string;
  timerType: "doctor" | "simulation";
  onTimeUp?: () => void;
  /** Called once when FINAL_COUNTDOWN_SECONDS remain — the "wrap up" bell. */
  onFinalCountdown?: (secondsLeft: number) => void;
  /** False holds the clock where it is, e.g. until the patient joins. Defaults to true. */
  running?: boolean;
  /** What a held clock says; defaults to waiting for the patient. */
  stoppedLabel?: string;
  /**
   * Seconds of this phase the server says are already used. The clock is always
   * `duration - elapsedSeconds` measured against the wall clock, and the browser's storage is never
   * read or written, so a reload, a second tab, another attempt or the next person in the tab
   * cannot move it.
   */
  elapsedSeconds: number;
  /** This device's `Date.now()` at which `elapsedSeconds` was true (when the server's answer arrived). */
  measuredAtMs: number;
}

/** Last stretch of the countdown, shown in red so the user isn't cut off unawares. */
export const FINAL_COUNTDOWN_SECONDS = 30;

/** Warning toast thresholds (seconds left) for each phase. */
const WARNING_SECONDS = { doctor: 30, simulation: 360 } as const;

/** Which of the warning, final and time-up signals have fired this phase. */
const NOT_FIRED = () => ({ warning: false, final: false, timeUp: false });

function leftLabel(seconds: number): string {
  return seconds >= 120 ? `${seconds / 60} minutes left` : `${seconds} seconds left`;
}

/**
 * A phase countdown driven by the server's attempt timing.
 *
 * Custom durations are applied by whoever derives the practice attempt's phases (see
 * `capabilities/attempt-runner`'s `usePracticeTimers`) and arrive here as `duration`; a circuit's
 * clock is never extended, because one clock serves everybody on it (`docs/BACKLOG.md`, S-2).
 */
export default function Timer({
  duration,
  stationId,
  timerType,
  onTimeUp,
  onFinalCountdown,
  running = true,
  stoppedLabel = "Starts with the patient",
  elapsedSeconds,
  measuredAtMs,
}: TimerProps) {
  // Parents pass inline callbacks; reading them through refs keeps the countdown
  // effect from re-registering (and restarting its interval) on every render.
  const onTimeUpRef = useRef(onTimeUp);
  const onFinalCountdownRef = useRef(onFinalCountdown);
  useEffect(() => {
    onTimeUpRef.current = onTimeUp;
    onFinalCountdownRef.current = onFinalCountdown;
  }, [onTimeUp, onFinalCountdown]);

  const serverLeft = () => secondsLeft(phaseDeadline(duration, elapsedSeconds, measuredAtMs), Date.now());
  const [timeRemaining, setTimeRemaining] = useState(serverLeft);
  // Mirrors `timeRemaining` for the ticker; the reset-on-new-answer effect must stay above the ticker effect.
  // Seconds left while held; the deadline is taken from it whenever the clock (re)starts.
  const heldRef = useRef(timeRemaining);
  const firedRef = useRef(NOT_FIRED());
  // Bumped by a reset so the ticker restarts from the full phase.
  const [restarts, setRestarts] = useState(0);
  const [confirmResetOpen, setConfirmResetOpen] = useState(false);
  const toast = useToast();

  // A new answer from the server replaces whatever the clock said (a reset included), aged from
  // when it arrived, so a remount long after the brief was read does not hand time back.
  useEffect(() => {
    const left = serverLeft();
    heldRef.current = left;
    firedRef.current = NOT_FIRED();
    setTimeRemaining(left);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [duration, elapsedSeconds, measuredAtMs]);

  const handleReset = () => {
    heldRef.current = duration;
    firedRef.current = NOT_FIRED();
    setTimeRemaining(duration);
    setRestarts((count) => count + 1);
  };

  // Measured from a wall-clock deadline, so a throttled background tab is right the moment it wakes.
  useEffect(() => {
    if (!running) return;
    const deadline = Date.now() + heldRef.current * 1000;
    const tick = () => {
      const left = secondsLeft(deadline, Date.now());
      heldRef.current = left;
      setTimeRemaining(left);
    };
    const id = window.setInterval(tick, 1000);
    const onVisible = () => {
      if (document.visibilityState === "visible") tick();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [running, duration, elapsedSeconds, measuredAtMs, restarts]);

  // Each signal fires once when its threshold is crossed (a woken tab can jump past the exact second).
  useEffect(() => {
    if (!running) return;
    const fired = firedRef.current;
    if (!fired.warning && timeRemaining > 0 && timeRemaining <= WARNING_SECONDS[timerType]) {
      fired.warning = true;
      toast.show({
        id: `timer-warning-${timerType}-${stationId}`,
        tone: "warning",
        title: leftLabel(WARNING_SECONDS[timerType]),
        message:
          timerType === "doctor"
            ? "Get ready: the consultation starts next."
            : "Start bringing the consultation towards management and safety-netting.",
        durationMs: 8000,
      });
    }
    if (!fired.final && timeRemaining > 0 && timeRemaining <= FINAL_COUNTDOWN_SECONDS) {
      fired.final = true;
      onFinalCountdownRef.current?.(timeRemaining);
    }
    if (!fired.timeUp && timeRemaining === 0) {
      fired.timeUp = true;
      onTimeUpRef.current?.();
    }
  }, [timeRemaining, running, timerType, stationId, toast]);

  // Calculate minutes and seconds for display
  const minutes = Math.floor(timeRemaining / 60);
  const seconds = timeRemaining % 60;
  const isFinalCountdown =
    timeRemaining > 0 && timeRemaining <= FINAL_COUNTDOWN_SECONDS;
  const isUrgent = isFinalCountdown || timeRemaining === 0;
  const digitClass = isUrgent ? "text-osce-danger" : "text-osce-ink-900";

  const phase = timerType === "simulation" ? "Consultation" : "Reading time";
  const label = !running
    ? stoppedLabel
    : isFinalCountdown
      ? timerType === "simulation"
        ? "Ending soon"
        : "Almost up"
      : phase;

  return (
    <div className="relative flex flex-col items-start sm:items-end">
      <div className="flex items-center gap-1.5">
        <span
          className={`font-mono text-osce-micro font-medium uppercase tracking-[0.08em] ${
            isFinalCountdown ? "text-osce-danger" : "text-b2c-text-muted"
          }`}
        >
          {label}
        </span>
        {running && (
          <button
            type="button"
            onClick={() => setConfirmResetOpen(true)}
            className="flex items-center justify-center rounded-sm text-b2c-text-muted transition-colors hover:text-osce-accent"
            title="Reset timer"
            aria-label="Reset timer"
          >
            <FiRotateCcw className="h-3.5 w-3.5" aria-hidden />
          </button>
        )}
      </div>
      <span
        className={`font-mono text-[28px] font-medium leading-[34px] tabular-nums ${digitClass} ${
          isFinalCountdown ? "animate-pulse" : ""
        }`}
      >
        {minutes.toString().padStart(2, "0")}:{seconds.toString().padStart(2, "0")}
      </span>
      {/* Announced once when the final countdown starts, not every second. */}
      <span className="sr-only" role="status" aria-live="assertive">
        {isFinalCountdown && timeRemaining === FINAL_COUNTDOWN_SECONDS
          ? `${FINAL_COUNTDOWN_SECONDS} seconds remaining`
          : ""}
      </span>

      <ConfirmModal
        isOpen={confirmResetOpen}
        onCancel={() => setConfirmResetOpen(false)}
        onConfirm={() => {
          setConfirmResetOpen(false);
          handleReset();
        }}
        title="Reset the timer?"
        message="This restores the full time for this phase on this screen; reloading the page goes back to the attempt's own clock. Use it only if you started by mistake."
        confirmText="Reset timer"
        cancelText="Keep going"
      />
    </div>
  );
}
