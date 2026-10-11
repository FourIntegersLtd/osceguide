import type { UpdateMe } from "@/capabilities/account/api";

/** The Preferences switches, each one a field of `PATCH /me`. */
export type PreferenceField = "ai_training_consent" | "colleague_waiting_email" | "needs_extra_time";

export interface PracticeTimers {
  readingSeconds: number;
  simulationSeconds: number;
}

/**
 * The body one switch sends. `PATCH /me` applies only the fields it is sent, so each switch saves
 * on its own without a Save button. Extra reading time carries its timers only when it is turned
 * on; turning it off keeps the saved timers for next time.
 */
export function preferencePatch(field: PreferenceField, value: boolean, timers?: PracticeTimers): UpdateMe {
  if (field === "needs_extra_time" && value && timers) {
    return {
      needs_extra_time: true,
      custom_reading_seconds: timers.readingSeconds,
      custom_simulation_seconds: timers.simulationSeconds,
    };
  }
  return { [field]: value };
}
