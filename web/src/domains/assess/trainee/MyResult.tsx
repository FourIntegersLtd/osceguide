"use client";

import { useCallback, useState } from "react";
import { Alert, AsyncBoundary, Badge, Button, b2bTokens } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { saveBlob } from "@/foundation/platform-client";
import { acknowledgeResult, downloadMyResult, readMyResult } from "@/domains/assess/trainee/api";
import { outcomeTone } from "@/domains/assess/results/support";

/**
 * A candidate's own result, once it has been released and not before.
 *
 * What appears is the server's projection of the decision — `released_at`,
 * `assessment_outcome` and the rationale a course lead wrote. The disclosure
 * policy is deliberately not reproduced here: a frontend that decides what a
 * candidate may see about their own examination is a frontend that can be
 * wrong about it, and the retiring arm's result page did exactly that, reading
 * a `preview` object it assembled from the org's own decision record.
 *
 * Acknowledging is the candidate's, and it is one-way: there is no unread.
 */
export function MyResult({ sittingId }: { sittingId: string }) {
  const state = useAsync((signal) => readMyResult(sittingId, signal), [sittingId]);
  const [acknowledging, setAcknowledging] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const reload = state.reload;

  const downloadPdf = useCallback(async () => {
    setDownloading(true);
    setError(null);
    try {
      const file = await downloadMyResult(sittingId);
      saveBlob(file.blob, file.filename);
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setDownloading(false);
    }
  }, [sittingId]);

  const acknowledge = useCallback(async () => {
    setAcknowledging(true);
    setError(null);
    try {
      await acknowledgeResult(sittingId);
      reload();
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setAcknowledging(false);
    }
  }, [sittingId, reload]);

  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <header className="border-b border-b2b-border pb-4">
        <p className={b2bTokens.b2bEyebrow}>Your result</p>
        <h1 className={`mt-1 ${b2bTokens.b2bPageTitle}`}>Assessment outcome</h1>
      </header>

      <AsyncBoundary state={state}>
        {(result) =>
          result.released_at === null ? (
            <Alert tone="info" title="Not released yet">
              Your organisation has not released this result. You are told when it is, and nothing
              about it is decided here.
            </Alert>
          ) : (
            <section className="space-y-5 rounded-lg border border-b2b-border bg-b2b-surface p-4 sm:p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className={b2bTokens.b2bEyebrow}>Outcome</p>
                  <p className="mt-1 text-osce-title font-semibold text-b2b-headline">
                    {outcomeLabel(result.assessment_outcome)}
                  </p>
                </div>
                <Badge tone={outcomeTone(result.assessment_outcome)}>
                  {outcomeLabel(result.assessment_outcome)}
                </Badge>
              </div>

              {result.assessment_score != null ? (
                <div className="rounded-lg border border-b2b-border bg-b2b-subtle px-4 py-3">
                  <p className={b2bTokens.b2bEyebrow}>Assessment score</p>
                  <p className="mt-1 text-osce-title font-semibold text-b2b-headline">
                    {result.assessment_score.toFixed(1)}
                    <span className="text-osce-body font-medium text-b2b-mid"> / 100</span>
                  </p>
                </div>
              ) : null}

              {result.rationale ? (
                <div>
                  <h2 className={b2bTokens.b2bSectionTitle}>What was said</h2>
                  <p className="mt-2 whitespace-pre-wrap text-osce-body leading-relaxed text-b2b-graphite">
                    {result.rationale}
                  </p>
                </div>
              ) : null}

              <p className="text-osce-caption text-b2b-mid">
                Released {new Date(result.released_at).toLocaleString()}
              </p>

              {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}

              <div className="flex flex-wrap items-center gap-3 border-t border-border pt-4">
                <button
                  type="button"
                  onClick={() => void downloadPdf()}
                  disabled={downloading}
                  className="inline-flex items-center justify-center rounded-osce-md border border-border bg-surface px-3 py-2 text-osce-meta font-medium text-ink hover:bg-canvas focus:outline-none focus:ring-2 focus:ring-accent/40 disabled:opacity-60"
                >
                  {downloading ? "Preparing…" : "Download PDF"}
                </button>
                {result.acknowledged_at ? (
                  <Alert tone="success">
                    You acknowledged this on{" "}
                    {new Date(result.acknowledged_at).toLocaleDateString()}.
                  </Alert>
                ) : (
                  <Button
                    themeType="b2b"
                    variant="commit"
                    isLoading={acknowledging}
                    onClick={() => void acknowledge()}
                  >
                    I have read this
                  </Button>
                )}
              </div>
            </section>
          )
        }
      </AsyncBoundary>
    </div>
  );
}

/**
 * The outcome in words.
 *
 * A result that exists with no outcome on it is possible — a decision can be
 * released as withheld — so "recorded" is said rather than an empty heading.
 */
function outcomeLabel(outcome: string | null | undefined): string {
  if (!outcome) return "Recorded";
  return outcome.replace(/_/g, " ").replace(/^\w/, (letter) => letter.toUpperCase());
}
