"use client";

import { useCallback, useMemo, useState } from "react";
import { HiOutlinePaperAirplane } from "react-icons/hi2";
import { Alert, AsyncBoundary, Badge, Button, EmptyState, b2bTokens } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { readSittingReport, releaseDecision } from "@/domains/assess/results/api";
import type { CandidateReport, SittingReport } from "@/domains/assess/results/api";
import { CandidateCard } from "@/domains/assess/results/CandidateCard";
import { CohortRanking } from "@/domains/assess/results/CohortRanking";
import { evidenceFor, releasable } from "@/domains/assess/results/support";

/**
 * What a course lead reads back after an examination.
 *
 * One request carries the whole sitting — who sat what, whether it was marked,
 * what the reviewers agreed and where each decision stands — where the
 * retiring client assembled it from a cohort summary, a candidate pack per
 * person and a probe per slot.
 */
export function Results({ orgSlug, sittingId }: { orgSlug: string; sittingId: string }) {
  const state = useAsync(
    (signal) => readSittingReport(orgSlug, sittingId, signal),
    [orgSlug, sittingId],
  );

  return (
    <div className="flex w-full min-w-0 flex-col gap-5">
      <AsyncBoundary state={state}>
        {(report) => (
          <Report
            report={report}
            orgSlug={orgSlug}
            sittingId={sittingId}
            onChanged={state.reload}
          />
        )}
      </AsyncBoundary>
    </div>
  );
}

function Report({
  report,
  orgSlug,
  sittingId,
  onChanged,
}: {
  report: SittingReport;
  orgSlug: string;
  sittingId: string;
  onChanged: () => void;
}) {
  const candidates = report.candidates ?? [];
  const waiting = candidates.filter(releasable);

  return (
    <>
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-b2b-border pb-4">
        <div className="min-w-0">
          <h1 className={b2bTokens.b2bPageTitle}>Results</h1>
          <p className="mt-1 text-osce-caption text-b2b-mid">
            {report.sitting.name} · {report.totals.stations_marked} of {report.totals.stations}{" "}
            stations marked
          </p>
        </div>
        <Badge variant={report.totals.decisions_released === report.totals.candidates ? "success" : "neutral"}>
          {report.totals.decisions_released} of {report.totals.candidates} released
        </Badge>
      </header>

      {candidates.length === 0 ? (
        <EmptyState title="Nobody has sat this yet." />
      ) : (
        <>
          <CohortRanking orgSlug={orgSlug} sittingId={sittingId} />

          {waiting.length > 0 ? (
            <ReleaseAll
              // A fresh selection whenever who is waiting changes (after a release).
              key={waiting.map((candidate) => candidate.user_id).join(",")}
              orgSlug={orgSlug}
              sittingId={sittingId}
              waiting={waiting}
              onChanged={onChanged}
            />
          ) : null}

          <section className="space-y-2">
            <h2 className={b2bTokens.b2bEyebrow}>Candidates</h2>
            <ul className="flex flex-col gap-2">
              {candidates.map((candidate) => (
                <li key={candidate.user_id}>
                  <CandidateCard
                    orgSlug={orgSlug}
                    sittingId={sittingId}
                    candidate={candidate}
                    onChanged={onChanged}
                  />
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </>
  );
}

/**
 * Releasing signed-off decisions, several at once.
 *
 * Offers exactly what is signed off and not yet out, because that is the only
 * set the backend will accept anyway, each ticked by name so a lead can hold
 * one back (the retiring screen released a selection behind a
 * `window.confirm`). Each is released by its own request, so each emits its
 * own `candidate_result_released` exactly as a single release does. A
 * candidate whose marking moved since sign-off is refused by the backend and
 * named here rather than silently skipped.
 */
function ReleaseAll({
  orgSlug,
  sittingId,
  waiting,
  onChanged,
}: {
  orgSlug: string;
  sittingId: string;
  waiting: CandidateReport[];
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [failures, setFailures] = useState<string[]>([]);
  const [released, setReleased] = useState<number | null>(null);
  const [picked, setPicked] = useState<Set<string>>(
    () => new Set(waiting.map((candidate) => candidate.user_id)),
  );
  const chosen = useMemo(
    () => waiting.filter((candidate) => picked.has(candidate.user_id)),
    [waiting, picked],
  );
  const allPicked = chosen.length === waiting.length;

  const toggle = (userId: string) =>
    setPicked((current) => {
      const next = new Set(current);
      if (next.has(userId)) next.delete(userId);
      else next.add(userId);
      return next;
    });

  const release = useCallback(async () => {
    setBusy(true);
    setFailures([]);
    setReleased(null);
    const problems: string[] = [];
    let done = 0;

    // One at a time, and every failure kept: a release refused because the
    // evidence moved is the single most important thing this screen can say,
    // and a `Promise.all` would lose all but the first.
    for (const candidate of chosen) {
      if (!candidate.trainee_id) continue;
      try {
        await releaseDecision(orgSlug, sittingId, candidate.trainee_id, evidenceFor(candidate));
        done += 1;
      } catch (cause) {
        const name = candidate.name ?? candidate.email ?? "A candidate";
        problems.push(`${name}: ${errorMessage(cause instanceof Error ? cause : new Error(String(cause)))}`);
      }
    }

    setReleased(done);
    setFailures(problems);
    setBusy(false);
    onChanged();
  }, [orgSlug, sittingId, chosen, onChanged]);

  return (
    <section className="space-y-3 rounded-lg border border-b2b-border bg-b2b-cream/40 p-4 sm:p-5">
      <h2 className={b2bTokens.b2bSectionTitle}>
        {waiting.length} signed off and not yet released
      </h2>
      <p className="text-osce-body text-b2b-mid">
        Releasing lets each of them read their outcome. Untick anyone to hold back.
      </p>

      <fieldset className="space-y-2">
        <legend className="sr-only">Candidates to release</legend>
        {waiting.length > 1 ? (
          <label className="flex items-center gap-2 text-osce-caption font-medium text-b2b-headline">
            <input
              type="checkbox"
              checked={allPicked}
              disabled={busy}
              onChange={() =>
                setPicked(
                  allPicked ? new Set() : new Set(waiting.map((candidate) => candidate.user_id)),
                )
              }
            />
            All {waiting.length}
          </label>
        ) : null}
        <ul className="grid gap-1 sm:grid-cols-2">
          {waiting.map((candidate) => (
            <li key={candidate.user_id}>
              <label className="flex items-center gap-2 text-osce-body text-b2b-headline">
                <input
                  type="checkbox"
                  checked={picked.has(candidate.user_id)}
                  disabled={busy}
                  onChange={() => toggle(candidate.user_id)}
                />
                {candidate.name ?? candidate.email ?? "Candidate"}
              </label>
            </li>
          ))}
        </ul>
      </fieldset>

      {released !== null ? (
        <Alert tone={failures.length === 0 ? "success" : "warning"}>
          {released} released{failures.length > 0 ? `, ${failures.length} refused.` : "."}
        </Alert>
      ) : null}
      {failures.length > 0 ? (
        <Alert tone="danger" title="Not released">
          <ul className="list-inside list-disc space-y-1">
            {failures.map((failure) => (
              <li key={failure}>{failure}</li>
            ))}
          </ul>
        </Alert>
      ) : null}

      <Button
        themeType="b2b"
        variant="commit"
        isLoading={busy}
        disabled={busy || chosen.length === 0}
        onClick={() => void release()}
      >
        <HiOutlinePaperAirplane className="h-4 w-4 shrink-0" aria-hidden />
        {allPicked ? `Release all ${waiting.length}` : `Release ${chosen.length} selected`}
      </Button>
    </section>
  );
}
