"use client";

import { useCallback, useState } from "react";
import { Alert, AsyncBoundary, Button, ButtonLink } from "@/foundation/ui";
import {
  TraineeHead,
  TraineeHero,
  TraineePage,
} from "@/domains/assess/trainee/traineeBoard";
import { whenWords } from "@/domains/assess/trainee/support";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { saveBlob } from "@/foundation/platform-client";
import {
  acknowledgeResult,
  downloadMyResult,
  readMyResult,
} from "@/domains/assess/trainee/api";
import { ResultView } from "@/domains/assess/trainee/ResultView";
import Link from "next/link";
import { useSurface } from "@/capabilities";
import { useAssessWords } from "@/capabilities/assess-words";
import { activeMembership, useSession } from "@/foundation/session";
import { HireResult } from "@/domains/assess/trainee/HireResult";
import {
  acknowledgedCopy,
  resultDesc,
} from "@/domains/assess/trainee/hireCopy";
import { readMySittings } from "@/domains/assess/trainee/api";

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
  const { hrefFor, orgSlug } = useSurface();
  const w = useAssessWords();
  const { session } = useSession();
  const org = activeMembership(session)?.org_name ?? "your employer";
  // An employer's page is headed by the assessment's name, which only the sittings feed carries.
  const feed = useAsync(
    (signal) =>
      w.hiring ? readMySittings(orgSlug, signal) : Promise.resolve(null),
    [orgSlug, w.hiring],
  );
  const name = feed.data?.items?.find(
    (sitting) => sitting.id === sittingId,
  )?.name;
  const state = useAsync(
    (signal) => readMyResult(sittingId, signal),
    [sittingId],
  );
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

  const ack = acknowledgedCopy(org);

  return (
    <TraineePage label="Assessment outcome">
      {w.hiring ? (
        <div>
          <Link
            href={hrefFor("/trainee")}
            className="text-assess-label text-osce-accent"
          >
            {w.MyTraining}
          </Link>
        </div>
      ) : null}
      <TraineeHead
        eyebrow={
          w.hiring
            ? undefined
            : state.data?.released_at
              ? `Released ${whenWords(state.data.released_at)}`
              : "Your result"
        }
        title={w.hiring ? (name ?? "Your result") : "Assessment outcome"}
        desc={
          w.hiring && state.data?.released_at
            ? resultDesc(state.data.released_at, org)
            : undefined
        }
        acts={
          state.data?.released_at ? (
            <Button
              themeType="b2b"
              variant="secondary"
              onClick={() => void downloadPdf()}
              disabled={downloading}
            >
              {downloading ? "Preparing…" : "Download PDF"}
            </Button>
          ) : null
        }
      />

      {!state.loading && !state.error && state.data === null ? (
        <Alert tone="info" title="Not released yet">
          {w.hiring ? org : "Your organisation"} has not released this result.
          When it is, we email you at the address{" "}
          {w.hiring ? org : "your organisation"} holds for you.
        </Alert>
      ) : null}
      <AsyncBoundary state={state}>
        {(result) =>
          result.released_at === null ? (
            <Alert tone="info" title="Not released yet">
              {w.hiring ? org : "Your organisation"} has not released this
              result. When it is, we email you at the address{" "}
              {w.hiring ? org : "your organisation"} holds for you.
            </Alert>
          ) : (
            <>
              {error ? (
                <Alert tone="danger">{errorMessage(error)}</Alert>
              ) : null}
              {w.hiring ? (
                <>
                  {result.acknowledged_at ? (
                    <Alert tone="success" title={ack.title}>
                      {ack.body}
                    </Alert>
                  ) : null}
                  <HireResult
                    result={result}
                    org={org}
                    action={
                      result.acknowledged_at ? null : (
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
                  />
                </>
              ) : (
                <ResultView
                  result={result}
                  actions={
                    result.acknowledged_at ? (
                      <p className="text-osce-meta text-b2c-text-muted">
                        You read this on{" "}
                        {new Date(result.acknowledged_at).toLocaleDateString()}.
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
                />
              )}
              {w.hiring ? null : (
                <TraineeHero
                  eyebrow="Keep practising"
                  title="Practise on your own"
                  action={
                    <ButtonLink
                      themeType="b2b"
                      variant="secondary"
                      href={hrefFor("/trainee/practice")}
                    >
                      Self practice
                    </ButtonLink>
                  }
                >
                  Nothing you do here is marked for the record.
                </TraineeHero>
              )}
            </>
          )
        }
      </AsyncBoundary>
    </TraineePage>
  );
}
