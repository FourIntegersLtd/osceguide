"use client";

import { useSession } from "@/foundation/session";

/** A station's own reading and consultation lengths, in seconds. */
export interface PhaseSeconds {
  readingSeconds: number;
  simulationSeconds: number;
}

/**
 * A person's own timers, for their own practice.
 *
 * While "Extra reading time" is on (`users.needs_extra_time`), a custom reading
 * or consultation length (`custom_reading_seconds`, `custom_simulation_seconds`)
 * replaces the exam's own for every station. A timer that was never set keeps
 * the exam's length, and switching it off keeps the saved timers but stops
 * using them.
 *
 * It never touches a circuit's clock: a circuit runs one clock for everybody on
 * it, so stretching it for one candidate would stretch it for the rest. An
 * institution grants extra time in an examination hall through the circuit's
 * own timing instead. See `docs/BACKLOG.md`, S-2.
 */
export function usePracticeTimers(defaults: PhaseSeconds): PhaseSeconds {
  return practiceTimers(useSession().session?.user, defaults);
}

/** The same rule as {@link usePracticeTimers}, for a screen that only knows the exam's lengths once they have loaded. */
export function practiceTimers(
  user: { needs_extra_time?: boolean | null; custom_reading_seconds?: number | null; custom_simulation_seconds?: number | null } | null | undefined,
  defaults: PhaseSeconds,
): PhaseSeconds {
  if (!user?.needs_extra_time) return defaults;
  return {
    readingSeconds: positiveOr(user.custom_reading_seconds, defaults.readingSeconds),
    simulationSeconds: positiveOr(user.custom_simulation_seconds, defaults.simulationSeconds),
  };
}

function positiveOr(value: number | null | undefined, fallback: number): number {
  return value != null && value > 0 ? value : fallback;
}
