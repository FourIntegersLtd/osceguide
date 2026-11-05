"use client";

import { Alert, Button, Panel } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { RubricFeedback, type AttemptFeedbackRead } from "@/capabilities/feedback";
import { markingNotice, type MarkingState } from "@/domains/assess/results/slotReviewSteps";

/** The automatic marking beside the review form: the marks, or why there are none, with a retry when it failed. */
export function MarkingPanel({
  marking,
  failedReason,
  feedback,
  busy,
  disabled,
  error,
  onRetry,
}: {
  marking: MarkingState;
  failedReason?: string | null;
  feedback: AttemptFeedbackRead | null;
  busy: boolean;
  disabled: boolean;
  error: Error | null;
  onRetry: () => void;
}) {
  // Results arrive oldest first; the latest marking is the one to agree or disagree with.
  const result = feedback?.results?.at(-1) ?? null;
  // The same feedback the candidate reads, drawn from the same rubric.
  if (result && feedback?.rubric) {
    return <RubricFeedback rubric={feedback.rubric} result={result} heading="Automatic marking" narrow />;
  }
  return (
    <Panel
      padding="md"
      title={marking === "pending" ? "Marking" : marking === "failed" ? "Could not be marked" : undefined}
    >
      <p className="text-osce-body text-b2b-mid">{markingNotice(marking, failedReason)}</p>
      {marking === "failed" && (
        <div className="mt-3 flex flex-col gap-2">
          <div>
            <Button variant="secondary" onClick={onRetry} disabled={disabled}>
              {busy ? "Retrying..." : "Retry marking"}
            </Button>
          </div>
          {error && !busy && <Alert tone="danger">{errorMessage(error)}</Alert>}
        </div>
      )}
    </Panel>
  );
}
