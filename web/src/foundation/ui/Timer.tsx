"use client";

import { useState, useEffect, useRef } from "react";
import { FiRotateCcw } from "react-icons/fi";

import ConfirmModal from "@/foundation/ui/ConfirmModal";
import { useToast } from "@/foundation/hooks/useToast";

interface TimerProps {
  duration: number; // Default timer duration in seconds (e.g., 600 for 10 minutes)
  stationId: string; // Unique identifier for the station to track timer state per station
  timerType: "doctor" | "simulation"; // Type of timer to differentiate between doctor and simulation phases
  onTimeUp?: () => void; // Callback function called when timer reaches 0
  /** Called once when FINAL_COUNTDOWN_SECONDS remain — the "wrap up" bell. */
  onFinalCountdown?: (secondsLeft: number) => void;
}

/** Last stretch of the countdown, shown in red so the user isn't cut off unawares. */
export const FINAL_COUNTDOWN_SECONDS = 30;

/**
 * Timer component that displays a countdown timer with localStorage persistence.
 * Supports custom durations for users with accessibility needs and restores timer state
 * when the page is refreshed or user navigates away and returns.
 */
export default function Timer({
  duration: defaultDuration, // Default duration passed as prop (e.g., 600 seconds)
  stationId,
  timerType,
  onTimeUp,
  onFinalCountdown,
}: TimerProps) {
  // Parents pass inline callbacks; reading them through refs keeps the countdown
  // effect from re-registering (and restarting its interval) on every render.
  const onTimeUpRef = useRef(onTimeUp);
  const onFinalCountdownRef = useRef(onFinalCountdown);
  useEffect(() => {
    onTimeUpRef.current = onTimeUp;
    onFinalCountdownRef.current = onFinalCountdown;
  }, [onTimeUp, onFinalCountdown]);

  /*
   * The countdown the caller asked for.
   *
   * The retiring version fetched the person's accessibility settings from here
   * and extended the clock itself, which made a UI primitive issue a request
   * and meant the timer could disagree with whatever the attempt was actually
   * scheduled for. This stays dumb on purpose: a person's own custom timers
   * (`users.custom_reading_seconds`, `custom_simulation_seconds`) are applied
   * by whoever derives the practice attempt's phases — see
   * `capabilities/attempt-runner`'s `usePracticeTimers` — and the chosen
   * figure arrives here as `duration`.
   * A circuit's clock is never extended, because one clock serves everybody on
   * it (`docs/BACKLOG.md`, S-2).
   */
  const effectiveDuration = defaultDuration;

  // Current time remaining in seconds (what's displayed on screen)
  const [timeRemaining, setTimeRemaining] = useState(defaultDuration);

  /**
   * Initialize or restore timer state when component mounts or effective duration changes.
   *
   * Logic flow:
   * 1. If using custom duration: Always start fresh (ignore any saved state)
   * 2. If using default duration: Try to restore saved timer state
   *    - Calculate how much time has passed since last save
   *    - Subtract elapsed time from saved remaining time
   *    - Only restore if result is valid (> 0 and <= effective duration)
   * 3. If no valid saved state: Start with effective duration
   */
  useEffect(() => {
    // Case 1: User has custom duration - always reset to custom duration
    // This ensures custom timers always start fresh and don't use old default timer state
    if (effectiveDuration !== defaultDuration) {
      setTimeRemaining(effectiveDuration);
      // Save the fresh start time to localStorage
      localStorage.setItem(
        `timer-${timerType}-${stationId}`,
        effectiveDuration.toString(),
      );
      localStorage.setItem(
        `timer-timestamp-${timerType}-${stationId}`,
        Date.now().toString(),
      );
      return;
    }

    // Case 2: Using default duration - try to restore saved timer state
    const savedTimeRemainingStr = localStorage.getItem(
      `timer-${timerType}-${stationId}`,
    );
    const savedTimestampMsStr = localStorage.getItem(
      `timer-timestamp-${timerType}-${stationId}`,
    );

    if (savedTimeRemainingStr && savedTimestampMsStr) {
      // Parse saved values
      const savedTimeRemaining = parseInt(savedTimeRemainingStr); // Time remaining when saved (seconds)
      const savedTimestampMs = parseInt(savedTimestampMsStr); // When timer was saved (milliseconds)

      // Calculate how many seconds have passed since the timer was saved
      const currentTimestampMs = Date.now(); // Current time (milliseconds)
      const elapsedTimeMs = currentTimestampMs - savedTimestampMs; // Difference in milliseconds
      const elapsedSeconds = Math.floor(elapsedTimeMs / 1000); // Convert to seconds

      // Calculate what the remaining time should be now
      // savedTimeRemaining = time left when saved (e.g., 450 seconds)
      // elapsedSeconds = time that has passed since save (e.g., 20 seconds)
      // restoredTimeRemaining = current time left (e.g., 450 - 20 = 430 seconds)
      // Math.max ensures we never get negative values (timer expired)
      const restoredTimeRemaining = Math.max(
        savedTimeRemaining - elapsedSeconds,
        0,
      );

      // Only restore if the calculated remaining time is valid
      // Must be > 0 (timer hasn't expired) and <= effectiveDuration (sanity check)
      if (
        restoredTimeRemaining > 0 &&
        restoredTimeRemaining <= effectiveDuration
      ) {
        setTimeRemaining(restoredTimeRemaining);
        return;
      }
    }

    // Case 3: No valid saved state - start fresh with effective duration
    setTimeRemaining(effectiveDuration);
  }, [effectiveDuration, timerType, stationId, defaultDuration]);

  // Flag to show warning modal when timer reaches warning threshold
  const [showWarning, setShowWarning] = useState(false);
  const [confirmResetOpen, setConfirmResetOpen] = useState(false);
  const toast = useToast();

  // The mid-station warning is a toast, so it never blocks the consultation.
  useEffect(() => {
    if (!showWarning) return;
    toast.show({
      id: `timer-warning-${timerType}-${stationId}`,
      tone: "warning",
      title: timerType === "doctor" ? "30 seconds left" : "6 minutes left",
      message:
        timerType === "doctor"
          ? "Get ready: the consultation starts next."
          : "Start bringing the consultation towards management and safety-netting.",
      durationMs: 8000,
    });
    setShowWarning(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showWarning]);

  // Flag to prevent multiple calls to onTimeUp callback
  const [hasCalledTimeUp, setHasCalledTimeUp] = useState(false);
  const hasCalledFinalCountdownRef = useRef(false);

  /**
   * Reset timer to effective duration and clear saved state.
   * This is called when user clicks the reset button.
   */
  const handleReset = () => {
    setTimeRemaining(effectiveDuration);
    setHasCalledTimeUp(false);
    hasCalledFinalCountdownRef.current = false;

    // Save reset time to localStorage
    localStorage.setItem(
      `timer-${timerType}-${stationId}`,
      effectiveDuration.toString(),
    );
    localStorage.setItem(
      `timer-timestamp-${timerType}-${stationId}`,
      Date.now().toString(),
    );
  };

  // Warning thresholds (in seconds) for each timer type
  const DOCTOR_TIME_WARNING = 30; // 30 seconds remaining for doctor phase
  const SIMULATION_TIME_WARNING = 360; // 6 minutes (360 seconds) remaining for simulation phase

  /**
   * Main timer countdown logic.
   *
   * This effect:
   * 1. Shows warning modal when timer reaches warning threshold
   * 2. Calls onTimeUp callback when timer reaches 0
   * 3. Continuously updates localStorage with current time remaining
   * 4. Decrements timeRemaining every second
   *
   * Runs whenever timeRemaining changes (every second during countdown).
   */
  useEffect(() => {
    // Show warning modal when timer reaches warning threshold
    if (timerType === "doctor" && timeRemaining === DOCTOR_TIME_WARNING) {
      setShowWarning(true);
    } else if (
      timerType === "simulation" &&
      timeRemaining === SIMULATION_TIME_WARNING
    ) {
      setShowWarning(true);
    }

    // Final-countdown bell, once per run
    if (
      timeRemaining > 0 &&
      timeRemaining <= FINAL_COUNTDOWN_SECONDS &&
      !hasCalledFinalCountdownRef.current
    ) {
      hasCalledFinalCountdownRef.current = true;
      onFinalCountdownRef.current?.(timeRemaining);
    }

    // Handle timer reaching 0
    if (timeRemaining === 0 && !hasCalledTimeUp) {
      // Clear saved state since timer is complete
      localStorage.removeItem(`timer-${timerType}-${stationId}`);
      localStorage.removeItem(`timer-timestamp-${timerType}-${stationId}`);

      // Call onTimeUp callback only once. Doing it here (not inside the setState
      // updater below) keeps it out of StrictMode's double-invoked updaters.
      setHasCalledTimeUp(true);
      onTimeUpRef.current?.();
      return; // Don't start countdown if timer is at 0
    }

    // Save current timer state to localStorage every second
    // This allows timer to be restored if user refreshes or navigates away
    localStorage.setItem(
      `timer-${timerType}-${stationId}`,
      timeRemaining.toString(),
    );
    localStorage.setItem(
      `timer-timestamp-${timerType}-${stationId}`,
      Date.now().toString(),
    );

    // Start countdown interval that decrements timer every second
    const countdownInterval = setInterval(() => {
      setTimeRemaining((currentTimeRemaining) => {
        const newTimeRemaining = currentTimeRemaining - 1;

        // If timer reaches 0 or below, stop the interval; the effect above
        // fires onTimeUp when it sees 0.
        if (newTimeRemaining <= 0) {
          clearInterval(countdownInterval);
          return 0; // Ensure timer doesn't go negative
        }

        return newTimeRemaining;
      });
    }, 1000); // Run every 1000ms (1 second)

    // Cleanup: clear interval when component unmounts or dependencies change
    return () => clearInterval(countdownInterval);
  }, [timeRemaining, stationId, timerType, hasCalledTimeUp]);

  // Calculate minutes and seconds for display
  const minutes = Math.floor(timeRemaining / 60);
  const seconds = timeRemaining % 60;
  const isFinalCountdown =
    timeRemaining > 0 && timeRemaining <= FINAL_COUNTDOWN_SECONDS;
  const isUrgent = isFinalCountdown || timeRemaining === 0;
  const digitClass = isUrgent ? "text-osce-danger" : "text-osce-ink-900";

  return (
    <div className="relative">
      <div
        className={`relative w-32 h-20 flex-shrink-0 rounded-lg transition-colors ${
          isFinalCountdown ? "animate-pulse bg-osce-danger-bg" : ""
        }`}
      >
        {/* Timer display */}
        <div
          className={`absolute inset-0 flex flex-col items-center justify-center ${
            isUrgent ? "text-osce-danger" : ""
          }`}
        >
          <div className="mb-0.5 flex items-center gap-1.5">
            <span
              className={`text-osce-caption ${
                isFinalCountdown
                  ? "font-semibold text-osce-danger"
                  : "text-b2c-text-muted"
              }`}
            >
              {isFinalCountdown
                ? timerType === "simulation"
                  ? "ending soon"
                  : "almost up"
                : "remaining"}
            </span>
            {/* Reset button - resets timer to effective duration */}
            <button
              type="button"
              onClick={() => setConfirmResetOpen(true)}
              className="flex cursor-pointer items-center justify-center text-b2c-text-muted transition-all hover:scale-110 hover:text-osce-accent"
              title="Reset timer"
              aria-label="Reset timer"
            >
              <FiRotateCcw className="h-5 w-5" aria-hidden />
            </button>
          </div>
          <div className="flex items-baseline space-x-1">
            {/* Minutes display */}
            <span className={`text-osce-title font-bold ${digitClass}`}>
              {minutes}
            </span>
            <span className="text-osce-caption text-b2c-text-muted">min</span>
            {/* Seconds display (padded with leading zero) */}
            <span
              className={`ml-1 text-osce-title font-bold ${digitClass}`}
            >
              {seconds.toString().padStart(2, "0")}
            </span>
            <span className="text-osce-caption text-b2c-text-muted">sec</span>
          </div>
        </div>
      </div>
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
        message="This restores the full time for this phase. Use it only if you started by mistake."
        confirmText="Reset timer"
        cancelText="Keep going"
      />
    </div>
  );
}