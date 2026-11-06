"use client";

import { FoldSection, b2bTokens } from "@/foundation/ui";
import { machineSummaryLine, type ReviewForm } from "@/domains/assess/results/reviewForm";
import { reviewCard } from "@/domains/assess/results/resultsChrome";
import { errorMessage } from "@/foundation/hooks";
import { RubricFeedback, type AttemptFeedbackRead } from "@/capabilities/feedback";
import { markingNotice, type MarkingState } from "@/domains/assess/results/slotReviewSteps";
import { boardPad, boardAlert, boardButtonSmall } from "@/foundation/ui/boardKit";

/** The automatic marking beside the review form: the marks, or why there are none, with a retry when it failed. */
export function MarkingPanel({
  marking,
  failedReason,
  feedback,
  busy,
  disabled,
  error,
  onRetry,
  form,
}: {
  marking: MarkingState;
  failedReason?: string | null;
  feedback: AttemptFeedbackRead | null;
  busy: boolean;
  disabled: boolean;
  error: Error | null;
  onRetry: () => void;
  form?: ReviewForm | null;
}) {
  // Results arrive oldest first; the latest marking is the one to agree or disagree with.
  const result = feedback?.results?.at(-1) ?? null;
  // The same feedback the candidate reads, drawn from the same rubric.
  if (result && feedback?.rubric) {
    const summary = machineSummaryLine(form, result.payload ?? null);
    return (
      <div className={reviewCard}>
        <h2 className="text-base font-semibold leading-normal">Automatic marking</h2>
        {summary ? <div className={b2bTokens.assessMeta}>{summary}</div> : null}
        <FoldSection title="The marking in full" defaultOpen={false}>
          <RubricFeedback rubric={feedback.rubric} result={result} heading="Automatic marking" narrow showAll />
        </FoldSection>
      </div>
    );
  }
  return (
    <div className={boardPad}>
      {marking === "pending" || marking === "failed" ? (
        <h2 className="text-base font-semibold leading-[1.2]">{marking === "pending" ? "Marking" : "Could not be marked"}</h2>
      ) : null}
      <p className={b2bTokens.assessMeta}>{markingNotice(marking, failedReason)}</p>
      {marking === "failed" && (
        <div className="flex flex-col gap-2">
          <div>
            <button
              type="button"
              className={boardButtonSmall}
              onClick={onRetry}
              disabled={disabled}
            >
              {busy ? "Retrying..." : "Retry marking"}
            </button>
          </div>
          {error && !busy && <div role="alert" className={boardAlert("bad")}>{errorMessage(error)}</div>}
        </div>
      )}
    </div>
  );
}
