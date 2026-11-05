/** The New exam sheet's rules: its steps, where a saved draft resumes, timing ranges and the publish chain. */

export const NEW_EXAM_STEPS = ["Name", "Marking scheme", "Timings", "Publish"] as const;

/** Where a saved draft reopens: step 1 when nothing is saved, then the first step still to do. */
export function resumeStep(exam: { rubric_version_id?: string | null } | null): number {
  if (!exam) return 0;
  return exam.rubric_version_id ? 2 : 1;
}

/** `breakMin` is optional: an exam with no break set leaves the choice to each sitting. */
type Minutes = { reading: string; simulation: string; breakMin?: string };

function outside(value: string, max: number): boolean {
  const n = Number(value);
  return value.trim() === "" || !Number.isInteger(n) || n < 1 || n > max;
}

/** Limits the api enforces on the default timings, in minutes. */
export const MAX_READING_MIN = 30;
export const MAX_CONSULT_MIN = 180;

export const MAX_BREAK_MIN = 60;

export function timingProblem({ reading, simulation, breakMin }: Minutes): string | null {
  if (outside(reading, MAX_READING_MIN)) return `Reading time must be 1 to ${MAX_READING_MIN} minutes.`;
  if (outside(simulation, MAX_CONSULT_MIN)) return `Consultation must be 1 to ${MAX_CONSULT_MIN} minutes.`;
  if (breakMin && outside(breakMin, MAX_BREAK_MIN)) return `Break must be 1 to ${MAX_BREAK_MIN} minutes.`;
  return null;
}

export function timingsLine({ reading, simulation, breakMin }: Minutes): string {
  const line = `${reading} min reading · ${simulation} min consultation`;
  return breakMin ? `${line} · ${breakMin} min break` : line;
}

import type { PublishStep } from "@/capabilities/authoring/sections/examSteps";

/** What the screen says while each write runs, and which one to retry. */
export const PUBLISH_STEP_WORDS: Record<PublishStep, string> = {
  publish: "Publishing the exam",
  add: "Creating its programme",
  activate: "Making it available for scheduling",
  retire: "Taking it off scheduling",
};

/** Stored seconds as whole minutes, the unit every exam screen shows. */
export function toMinutes(seconds: number | string): number {
  return Math.round(Number(seconds) / 60);
}
