"use client";

import { useEffect, useState } from "react";
import { Alert, AsyncBoundary, Card, PageHeader, Spinner } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { FeedbackView, TranscriptView } from "@/capabilities/feedback";
import { readResult, readTranscript } from "@/capabilities/attempt-runner";

/**
 * A finished attempt: the marking, and what was said.
 *
 * Scoring runs as a background job, so a result that is not there yet is
 * expected rather than an error. This polls a few times and then tells the
 * person plainly, instead of showing an empty page that looks like a bug.
 */
export function AttemptResult({ attemptId }: { attemptId: string }) {
  const [attempt, setAttempt] = useState(0);

  const result = useAsync(
    async (signal) => {
      try {
        return await readResult(attemptId, signal);
      } catch (cause) {
        // `result_not_ready` is the scorer still working. Anything else is real.
        if (hasCode(cause, "not_found", "result_not_found")) return null;
        throw cause;
      }
    },
    [attemptId, attempt],
  );

  const transcript = useAsync((signal) => readTranscript(attemptId, signal), [attemptId]);

  useEffect(() => {
    if (result.data !== null || result.loading || result.error) return;
    if (attempt >= 10) return;
    // Backs off: scoring a long consultation takes longer than a short one, and
    // hammering the endpoint every second buys nothing.
    const delay = Math.min(30_000, 3_000 * (attempt + 1));
    const id = window.setTimeout(() => setAttempt((n) => n + 1), delay);
    return () => window.clearTimeout(id);
  }, [result.data, result.loading, result.error, attempt]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Your feedback" />

      {result.data === null && !result.error && (
        <Card>
          <div className="flex items-center gap-3 text-sm text-ink-muted">
            {attempt < 10 ? (
              <>
                <Spinner /> Your consultation is being marked. This usually takes a minute.
              </>
            ) : (
              "Marking is taking longer than usual. Come back shortly — your attempt is safe."
            )}
          </div>
        </Card>
      )}

      {result.error && <Alert tone="danger">We could not load your feedback.</Alert>}

      {result.data && <FeedbackView payload={result.data.payload} />}

      <AsyncBoundary state={transcript}>
        {(data) => <TranscriptView transcript={data} />}
      </AsyncBoundary>
    </div>
  );
}
