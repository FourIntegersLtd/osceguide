/** Where an exam stands on its way to being offered: the steps, and the one thing to do next. */

import type { RailStep } from "@/foundation/ui";

export type ExamStepId = "scheme" | "publish";

type ExamState = { status: string; rubric_version_id?: string | null; owner_kind?: string | null };

/** Picking a marking scheme, then publishing. "Used by a programme" is not known here, so it is not a step. */
export function examSteps(exam: ExamState): RailStep<ExamStepId>[] {
  const hasScheme = Boolean(exam.rubric_version_id);
  const published = exam.status === "published";
  const retired = exam.status === "retired";
  return [
    {
      id: "scheme",
      label: "Pick marking scheme",
      state: hasScheme ? "done" : "todo",
      note: hasScheme ? "Chosen" : "Not chosen",
    },
    {
      id: "publish",
      label: "Publish",
      state: published || retired ? "done" : "todo",
      note: retired ? "Retired" : published ? "Live" : "Draft",
    },
  ];
}

type ProgrammeState = { status: string } | null | undefined;

export type ExamChip = "Draft" | "Needs a marking scheme" | "Ready to schedule" | "Not available" | "Not adopted yet";

/** The exam, its marking scheme and its programme joined into one status. */
export function examChip(exam: ExamState, programme: ProgrammeState): ExamChip {
  if (exam.status === "draft") return exam.rubric_version_id ? "Draft" : "Needs a marking scheme";
  if (exam.status === "published" && programme?.status === "active") return "Ready to schedule";
  // A platform exam this organisation has not taken up has no programme of its own: not "unavailable".
  if (exam.owner_kind === "platform" && !programme) return "Not adopted yet";
  return "Not available";
}

export function toggleHelp(on: boolean): string {
  return on
    ? "On: this exam can be picked when you schedule a sitting."
    : "Off: existing sittings carry on, but no new ones can be scheduled.";
}

export type AvailabilityStep = "add" | "activate" | "retire";

/** The "Available for scheduling" switch is the programme's add, activate and retire. */
export function availabilityPlan(programme: ProgrammeState, on: boolean): AvailabilityStep[] {
  if (on) return !programme ? ["add", "activate"] : programme.status === "active" ? [] : ["activate"];
  return programme && programme.status === "active" ? ["retire"] : [];
}

export type PublishStep = "publish" | AvailabilityStep;

/**
 * Publishing and offering an exam, from wherever it stands: the writes still to do, in order.
 * Recomputed from fresh state, so a retry after a failure resumes at the step that failed.
 */
export function publishPlan(exam: { status: string }, programme: ProgrammeState): PublishStep[] {
  const offer = availabilityPlan(programme, true);
  return exam.status === "published" ? offer : ["publish", ...offer];
}

export type ExamNextAction = { id: "pick-scheme" | "publish" | "programme" | "none"; line: string };

export function examNextAction(exam: ExamState): ExamNextAction {
  if (exam.status === "retired") return { id: "none", line: "Retired. It is no longer offered for new sittings." };
  if (exam.status === "published") return { id: "programme", line: "Live. Add a programme for it so people can take it." };
  if (!exam.rubric_version_id) return { id: "pick-scheme", line: "Pick a marking scheme, then publish." };
  return { id: "publish", line: "Publish this exam to run sittings against it." };
}

/** The programme an exam is offered through, matched by the exam's id (a code is only unique per owner). */
export function programmeFor<P extends { exam_id: string }>(programmes: P[], exam: { id: string }): P | null {
  return programmes.find((programme) => programme.exam_id === exam.id) ?? null;
}
