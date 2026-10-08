/**
 * A station review's three marks in order: the automatic marking, this
 * person's own marks, and the admin's review (the one that counts). Pure, so
 * the words can be tested.
 */

import type { RailStep } from "@/foundation/ui";

export type SlotStepId = "auto" | "mine" | "admin";

export type SlotStep = RailStep<SlotStepId>;

/**
 * `none`: nobody took the station. `pending`: taken, marking not finished. `failed`: marking
 * gave up after its retries; a reviewer can queue it again.
 * `unmarkable`: taken, but the attempt failed for want of a marking scheme, so there is nothing to
 * retry; the station has to be sat again.
 * `unavailable`: marked without a marking scheme, so there are no automatic
 * marks and there will not be. `ready`: marks to read.
 */
export type MarkingState = "none" | "pending" | "failed" | "unmarkable" | "unavailable" | "ready";

export type FormStatus = "none" | "draft" | "completed";

export function markingState(input: {
  attemptId: string | null;
  hasResult: boolean;
  hasRubric: boolean;
  markingFailed?: boolean;
  /** Why the slot's last attempt failed when it has no live one (`SlotReviewsRead.attempt_failed_reason`). */
  failedReason?: string | null;
}): MarkingState {
  if (!input.attemptId) return input.failedReason ? "unmarkable" : "none";
  if (!input.hasResult) return input.markingFailed ? "failed" : "pending";
  return input.hasRubric ? "ready" : "unavailable";
}

/** What the automatic marking panel says when there is nothing to show. */
export function markingNotice(state: MarkingState): string | null {
  switch (state) {
    case "none":
      return "Nobody has taken this station, so there is no automatic marking.";
    case "pending":
      return "Automatic marking is not ready yet. It appears here when it finishes.";
    case "failed":
      return "Automatic marking failed. Retry it, or mark this station without it.";
    case "unmarkable":
      return "This station was taken, but it could not be marked because its exam had no marking scheme. It needs to be sat again; you can still record your own marks.";
    case "unavailable":
      return "This station was taken before the exam had a marking scheme, so there are no automatic marks and there will not be.";
    case "ready":
      return null;
  }
}

const AUTO: Record<MarkingState, Pick<SlotStep, "state" | "note">> = {
  none: { state: "todo", note: "Not taken" },
  pending: { state: "todo", note: "Not ready yet" },
  failed: { state: "attention", note: "Marking failed" },
  unmarkable: { state: "attention", note: "Could not be marked" },
  unavailable: { state: "attention", note: "Not available" },
  ready: { state: "done", note: "Ready" },
};

const FORM: Record<FormStatus, Pick<SlotStep, "state" | "note">> = {
  none: { state: "todo", note: "Not started" },
  draft: { state: "todo", note: "Draft" },
  completed: { state: "done", note: "Submitted" },
};

/** `admin` is null for someone who does not write the admin's review: that step is not theirs, so it is not shown. */
export function slotReviewSteps(input: { marking: MarkingState; mine: FormStatus; admin: FormStatus | null }): SlotStep[] {
  const steps: SlotStep[] = [
    { id: "auto", label: "Automatic marking", ...AUTO[input.marking] },
    { id: "mine", label: "Your marks", ...FORM[input.mine] },
  ];
  if (input.admin !== null) steps.push({ id: "admin", label: "Admin's review", ...FORM[input.admin] });
  return steps;
}

/** The one form that is open for this person; the other is read-only. */
export function openForm(isAdmin: boolean): "mine" | "admin" {
  return isAdmin ? "admin" : "mine";
}

/** The one thing to do next, for the form that is open. */
export function slotNextLine(open: "mine" | "admin", steps: SlotStep[]): string {
  const done = steps.find((step) => step.id === open)?.state === "done";
  if (open === "mine") return done ? "Your marks are submitted." : "Rate each area, then submit your marks.";
  return done ? "The admin's review is complete." : "Write the admin's review, then complete it.";
}
