"use client";

import { useState } from "react";
import { Alert, AsyncBoundary, Button } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { TraineeList } from "@/domains/assess/trainee/traineeBoard";
import { readMyAppeal, requestMyAppeal } from "@/domains/assess/trainee/api";
import { candidateAppealLine } from "@/domains/assess/results/appealsView";
import { useAssessWords } from "@/domains/assess/useAssessWords";
import { boardInput, boardLabel } from "@/foundation/ui/boardKit";

/**
 * Asking for a released result to be looked at again.
 *
 * One request at a time: once made, this shows where it has got to and what came of it. The
 * organisation's second marker is never named here, and what they decided is added to the result
 * as a new revision rather than replacing the one the candidate first read.
 */
export function RequestReview({ sittingId }: { sittingId: string }) {
  const w = useAssessWords();
  const state = useAsync(async (signal) => ({ appeal: await readMyAppeal(sittingId, signal) }), [sittingId]);
  const [asking, setAsking] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await requestMyAppeal(sittingId, reason.trim());
      setAsking(false);
      setReason("");
      state.reload();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <TraineeList title="Ask for a review">
      <AsyncBoundary state={state}>
        {({ appeal }) =>
          appeal ? (
            <div className="flex flex-col gap-2" role="status">
              <p className="m-0 font-medium">{candidateAppealLine(appeal.status)}</p>
              <p className="m-0 whitespace-pre-wrap text-osce-meta text-b2c-text-muted">You wrote: {appeal.reason}</p>
              {appeal.decision_note ? (
                <p className="m-0 whitespace-pre-wrap">The organisation wrote: {appeal.decision_note}</p>
              ) : null}
            </div>
          ) : asking ? (
            <div className="flex flex-col gap-3">
              <label htmlFor="review-reason" className={boardLabel}>
                Why should this result be looked at again?
              </label>
              <textarea
                id="review-reason"
                className={boardInput}
                rows={4}
                maxLength={4000}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
              {error ? <Alert tone="danger">{error}</Alert> : null}
              <div className="flex gap-2">
                <Button themeType="b2b" variant="commit" isLoading={busy} disabled={reason.trim() === ""} onClick={() => void submit()}>
                  Send request
                </Button>
                <Button themeType="b2b" variant="secondary" disabled={busy} onClick={() => setAsking(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-start gap-2">
              <p className="m-0 text-osce-meta text-b2c-text-muted">
                {`If you think this result is wrong, ask the ${w.hiring ? "employer" : "organisation"} to have it looked at by a second marker.`}
              </p>
              <Button themeType="b2b" variant="secondary" onClick={() => setAsking(true)}>
                Ask for a review
              </Button>
            </div>
          )
        }
      </AsyncBoundary>
    </TraineeList>
  );
}
