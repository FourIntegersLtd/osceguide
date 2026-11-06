import type { MarkedResult, MarkingRubric, Rating, ResultTotals } from "@/capabilities/feedback";
import type { RubricPreview, TrialMark } from "@/capabilities/authoring/api";

/**
 * Feeding the builder's drafts to the screens a candidate will see.
 *
 * The preview does not draw its own imitation of the feedback page: it hands
 * the real `RubricFeedback` a rubric and a result shaped exactly like the
 * ones an attempt reads (`MarkingRubricRead`, `MarkedResultRead`). The
 * rubric is the draft as the backend normalised it; the result is the
 * backend's made-up `sample_result` (or a trial mark's `marks`) with the totals
 * the backend computed for it. So what an author sees is what a candidate
 * will see, from the same code.
 */

/** What `RubricFeedback` and the dashboard preview both need. */
export interface FeedbackInputs {
  rubric: MarkingRubric;
  result: MarkedResult;
  rating: Rating;
  display: Record<string, unknown>;
  totals: ResultTotals | null;
}

function inputs(
  rating: Rating,
  structure: Record<string, unknown>,
  display: Record<string, unknown>,
  payload: Record<string, unknown>,
  totals: ResultTotals | null,
  modelUsed: string | null,
): FeedbackInputs {
  return {
    rubric: { version_id: null, rating, structure, display },
    result: {
      // Not a stored result: these two name what it is, for anyone debugging the screen.
      framework_id: "rubric-preview",
      policy_version: "preview",
      model_used: modelUsed,
      scored_at: "",
      payload,
      totals,
    },
    rating,
    display,
    totals,
  };
}

/**
 * The sample result a valid draft renders as, or null while the draft has
 * problems (the backend sends no sample for a structure it cannot read).
 */
export function previewInputs(preview: RubricPreview | null): FeedbackInputs | null {
  if (!preview?.valid || !preview.rating || !preview.sample_result) return null;
  return inputs(
    preview.rating,
    preview.structure ?? {},
    preview.display ?? {},
    preview.sample_result,
    preview.sample_totals ?? null,
    null,
  );
}

/**
 * A finished trial mark drawn on the draft it marked against, or null until
 * it has finished. The rubric side comes from the latest valid preview,
 * because the trial answers marks and totals only.
 */
export function trialInputs(trial: TrialMark | null, preview: RubricPreview | null): FeedbackInputs | null {
  if (!trial || trial.status !== "marked" || !trial.marks) return null;
  if (!preview?.rating) return null;
  return inputs(
    preview.rating,
    preview.structure ?? {},
    preview.display ?? {},
    trial.marks,
    trial.totals ?? null,
    trial.model_used ?? null,
  );
}
