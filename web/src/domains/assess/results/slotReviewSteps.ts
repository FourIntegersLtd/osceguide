/**
 * A station review's three marks in order: the automatic marking, this
 * person's own marks, and the admin's review (the one that counts). Pure, so
 * the words can be tested.
 */

import type { RailStep } from "@/foundation/ui";
import type { AssessWords } from "@/capabilities/assess-words/vocabulary";

export type SlotStepId = "auto" | "mine" | "admin";

export type SlotStep = RailStep<SlotStepId>;

/**
 * `none`: nobody took the station. `pending`: taken, marking not finished. `failed`: marking
 * gave up after its retries; a reviewer can queue it again.
 * `unmarkable`: taken, but the attempt itself failed (no marking scheme, an empty transcript), so
 * there is nothing to retry.
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
export function markingNotice(
  state: MarkingState,
  failedReason: string | null | undefined,
  w: AssessWords,
): string | null {
  if (w.hiring) {
    switch (state) {
      case "pending":
        return "You can mark now, or wait. This page updates when the AI mark arrives.";
      case "failed":
        return "The recording finished, but marking failed. Try again, or mark it yourself.";
      case "unmarkable":
        return failedReason === "no_marking_rubric"
          ? "This station cannot be marked automatically because the exam had no marking scheme when it was sat. Ask the candidate to sit it again, or enter your own marks."
          : "Automatic marking failed for this station. Enter your own marks, or ask support if this keeps happening.";
      case "unavailable":
        return "There are no automatic marks for this station because it was sat before the exam had a marking scheme. Enter your own marks.";
      default:
        break;
    }
  }
  switch (state) {
    case "none":
      return "Nobody has taken this station, so there is no automatic marking.";
    case "pending":
      return "The AI mark is on its way. This page updates on its own.";
    case "failed":
      return "This station could not be marked.";
    case "unmarkable":
      return failedReason === "no_marking_rubric"
        ? "This station was taken, but it could not be marked because its exam had no marking scheme. It needs to be sat again; you can still record your own marks."
        : `This station was taken, but it could not be marked (${failedReason ?? "unknown reason"}). You can still record your own marks.`;
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

/** One form per person: an admin (`admin` not null) writes only the admin's review, anyone else only their own marks. */
export function slotReviewSteps(
  input: { marking: MarkingState; mine: FormStatus; admin: FormStatus | null },
  w: AssessWords,
): SlotStep[] {
  const auto: SlotStep = { id: "auto", label: "Automatic marking", ...AUTO[input.marking] };
  if (input.admin !== null) return [auto, { id: "admin", label: leadReviewLabel(w), ...FORM[input.admin] }];
  return [auto, { id: "mine", label: "Your marks", ...FORM[input.mine] }];
}

/** The lead's review: the admin's on an institution, the lead assessor's on hire. */
export function leadReviewLabel(w: AssessWords): string {
  return w.hiring ? `${w.LeadSupervisor}'s review` : "Admin's review";
}

/** The marking card's heading while there is nothing to show; the board's words on hire. */
export function markingHeading(state: MarkingState, w: AssessWords): string {
  if (w.hiring) return state === "pending" ? "The AI is still marking this station" : "The AI could not mark this station";
  return state === "pending" ? "Marking" : "Could not be marked";
}

/** The retry button's words. */
export function retryLabel(busy: boolean, w: AssessWords): string {
  return busy ? "Retrying..." : w.hiring ? "Try marking again" : "Retry marking";
}

/** What sits beneath a disabled primary button, hire only (an institution submits and is refused by the api). */
export function submitHint(missing: number, w: AssessWords): string | null {
  return w.hiring && missing > 0 ? "Submit needs a rating on every competency." : null;
}

/** The one form that is open for this person; the other is read-only. */
export function openForm(isAdmin: boolean): "mine" | "admin" {
  return isAdmin ? "admin" : "mine";
}

/** The one thing to do next, for the form that is open. */
export function slotNextLine(open: "mine" | "admin", steps: SlotStep[], w: AssessWords): string {
  const done = steps.find((step) => step.id === open)?.state === "done";
  if (open === "mine") return done ? "Your marks are submitted." : "Rate each area, then submit your marks.";
  if (w.hiring) return done ? `The ${w.leadSupervisor}'s review is complete.` : "Write your review, then choose Complete.";
  return done ? "The admin's review is complete." : "Write the admin's review, then complete it.";
}

/** The disagreement notice: who, how many competencies, and who settles it. */
export function disagreementCopy(
  other: { name: string; count: number },
  you: string,
  w: AssessWords,
): { title: string; body: string } {
  const noun = other.count === 1 ? "competency" : "competencies";
  return {
    title: `${you} and ${other.name} disagree on ${other.count} ${noun}`,
    body: w.hiring
      ? `The ${w.leadSupervisor} settles it. Their mark is the one that counts.`
      : "The admin's review settles it. It is the mark that counts.",
  };
}

export const LEAD_DECIDES = "Lead decides";

/** The assessor rated a competency differently from the AI; an unrated or unmarked one is not a disagreement. */
export function aiDisagrees(machine: unknown, mine: unknown): boolean {
  return machine != null && mine != null && machine !== mine;
}
