/** The New exam sheet's rules: its steps, where a saved draft resumes, timing ranges and the publish chain. */

export const NEW_EXAM_STEPS = ["Name", "Marking scheme", "Timings", "Publish"] as const;

/** Where a saved draft reopens: step 1 when nothing is saved, then the first step still to do. */
export function resumeStep(exam: { rubric_version_id?: string | null } | null): number {
  if (!exam) return 0;
  return exam.rubric_version_id ? 2 : 1;
}

type Minutes = { reading: string; simulation: string };

function outside(value: string, max: number): boolean {
  const n = Number(value);
  return value.trim() === "" || !Number.isInteger(n) || n < 1 || n > max;
}

/** Limits the api enforces on the default timings, in minutes. */
export const MAX_READING_MIN = 30;
export const MAX_CONSULT_MIN = 180;

export function timingProblem({ reading, simulation }: Minutes): string | null {
  if (outside(reading, MAX_READING_MIN)) return `Reading time must be 1 to ${MAX_READING_MIN} minutes.`;
  if (outside(simulation, MAX_CONSULT_MIN)) return `Consultation must be 1 to ${MAX_CONSULT_MIN} minutes.`;
  return null;
}

export function timingsLine({ reading, simulation }: Minutes): string {
  return `${reading} min reading · ${simulation} min consultation`;
}

export type PublishStep = "publish" | "programme" | "activate" | "done";

/** Publishing is three writes; this names the first one not yet done, so a retry resumes there. */
export function nextPublishStep(
  exam: { status: string },
  programme: { status: string } | null,
): PublishStep {
  if (exam.status !== "published") return "publish";
  if (!programme) return "programme";
  return programme.status === "active" ? "done" : "activate";
}

export const PUBLISH_STEP_WORDS: Record<Exclude<PublishStep, "done">, string> = {
  publish: "Publishing the exam",
  programme: "Creating its programme",
  activate: "Making it available for scheduling",
};
