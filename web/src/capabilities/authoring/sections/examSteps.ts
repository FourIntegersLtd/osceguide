/** Where an exam stands on its way to being offered: the steps, and the one thing to do next. */

import type { RailStep } from "@/foundation/ui";

export type ExamStepId = "scheme" | "publish";

type ExamState = { status: string; rubric_version_id?: string | null };

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

export type ExamChip = "Draft" | "Needs a marking scheme" | "Ready to schedule" | "Not available";

/** The exam, its marking scheme and its programme joined into one status. */
export function examChip(exam: ExamState, programme: ProgrammeState): ExamChip {
  if (exam.status === "draft") return exam.rubric_version_id ? "Draft" : "Needs a marking scheme";
  if (exam.status === "published" && programme?.status === "active") return "Ready to schedule";
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
  if (on) return programme ? ["activate"] : ["add", "activate"];
  return programme && programme.status === "active" ? ["retire"] : [];
}

export type ExamNextAction = { id: "pick-scheme" | "publish" | "programme" | "none"; line: string };

export function examNextAction(exam: ExamState): ExamNextAction {
  if (exam.status === "retired") return { id: "none", line: "Retired. It is no longer offered for new sittings." };
  if (exam.status === "published") return { id: "programme", line: "Live. Add a programme for it so people can take it." };
  if (!exam.rubric_version_id) return { id: "pick-scheme", line: "Pick a marking scheme, then publish." };
  return { id: "publish", line: "Publish this exam to run sittings against it." };
}
