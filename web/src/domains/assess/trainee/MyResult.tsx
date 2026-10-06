"use client";

import { useCallback, useState } from "react";
import { Alert, AsyncBoundary, B2CHero, B2CPageHeader, Button, ButtonLink } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { saveBlob } from "@/foundation/platform-client";
import { acknowledgeResult, downloadMyResult, readMyResult } from "@/domains/assess/trainee/api";
import { workspaceBasePath } from "@/foundation/routing";
import { useSurface } from "@/capabilities";

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
  const { hrefFor } = useSurface();
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
      <B2CPageHeader
        className="!mb-0"
        eyebrow={
          state.data?.released_at
            ? `Released ${new Date(state.data.released_at).toLocaleDateString()}`
            : "Your result"
        }
        title="Assessment outcome"
        action={
          state.data?.released_at ? (
            <button
              type="button"
              onClick={() => void downloadPdf()}
              disabled={downloading}
              className="inline-flex items-center justify-center rounded-control border border-b2b-border bg-b2b-surface px-3 py-2 text-osce-meta font-medium text-b2b-headline hover:bg-canvas focus:outline-none disabled:opacity-60"
            >
              {downloading ? "Preparing…" : "Download PDF"}
            </button>
          ) : null
        }
      />

      {!state.loading && !state.error && state.data === null ? (
        <Alert tone="info" title="Not released yet">
          Your organisation has not released this result. You are told when it is, and nothing
          about it is decided here.
        </Alert>
      ) : null}
      <AsyncBoundary state={state}>
        {(result) =>
          result.released_at === null ? (
            <Alert tone="info" title="Not released yet">
              Your organisation has not released this result. You are told when it is, and nothing
              about it is decided here.
            </Alert>
          ) : (
            <>
              {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}
              <B2CHero
                eyebrow="Outcome"
                title={
                  result.assessment_score != null
                    ? `${outcomeLabel(result.assessment_outcome)}, ${result.assessment_score.toFixed(1)} / 100`
                    : outcomeLabel(result.assessment_outcome)
                }
                action={
                  result.acknowledged_at ? (
                    <p className="text-osce-meta text-b2c-text-muted">
                      You read this on {new Date(result.acknowledged_at).toLocaleDateString()}.
                    </p>
                  ) : (
                    <Button
                      themeType="b2b"
                      variant="commit"
                      isLoading={acknowledging}
                      onClick={() => acknowledge()}
                    >
                      I have read this
                    </Button>
                  )
                }
              >
                {result.rationale ? (
                  <span className="whitespace-pre-wrap">{result.rationale}</span>
                ) : null}
              </B2CHero>
              <B2CHero
                eyebrow="Keep practising"
                title="Practise on your own"
                action={
                  <>
                    <ButtonLink
                      themeType="b2b"
                      variant="secondary"
                      size="sm"
                      href={hrefFor("/trainee/practice")}
                    >
                      Self practice
                    </ButtonLink>
                    <ButtonLink
                      themeType="b2b"
                      variant="secondary"
                      size="sm"
                      href={`${workspaceBasePath("me")}/dashboard`}
                    >
                      Open personal practice
                    </ButtonLink>
                  </>
                }
              >
                Nothing you do here is marked for the record.
              </B2CHero>
            </>
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
