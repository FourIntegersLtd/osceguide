"use client";

import { useCallback, useMemo, useState } from "react";
import { HiOutlinePaperAirplane } from "react-icons/hi2";
import { Alert, AsyncBoundary, B2CHero, B2CPageHeader, Button, EmptyState, b2bTokens, Panel } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { saveBlob } from "@/foundation/platform-client";
import { downloadSittingResults, readSittingReport, releaseDecisions } from "@/domains/assess/results/api";
import type { CandidateReport, SittingReport } from "@/domains/assess/results/api";
import { CandidateCard } from "@/domains/assess/results/CandidateCard";
import { CohortRanking } from "@/domains/assess/results/CohortRanking";
import { evidenceFor, releasable, releaseRefusal } from "@/domains/assess/results/support";

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
  const { hrefFor } = useSurface();
  const candidates = report.candidates ?? [];
  const waiting = candidates.filter(releasable);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const downloadCsv = useCallback(async () => {
    setDownloading(true);
    setDownloadError(null);
    try {
      const file = await downloadSittingResults(orgSlug, sittingId);
      saveBlob(file.blob, file.filename);
    } catch (cause) {
      setDownloadError(errorMessage(cause));
    } finally {
      setDownloading(false);
    }
  }, [orgSlug, sittingId]);

  return (
    <>
      <B2CPageHeader
        back={{ href: hrefFor(`/sittings/${sittingId}`), label: "Sitting" }}
        eyebrow={report.sitting.name}
        title="Results"
        subtitle={`${report.totals.stations_marked} of ${report.totals.stations} stations marked · ${report.totals.decisions_released} of ${report.totals.candidates} released`}
        action={
          <Button
            themeType="b2b"
            variant="secondary"
            isLoading={downloading}
            disabled={downloading}
            onClick={() => downloadCsv()}
          >
            Download CSV
          </Button>
        }
      />
      {downloadError ? <Alert tone="danger">{downloadError}</Alert> : null}

      {candidates.length === 0 ? (
        <EmptyState title="Nobody has sat this yet." />
      ) : (
        <>
          <OutcomeTiles candidates={candidates} awaitingMarking={report.totals.awaiting_marking} />

          {waiting.length > 0 ? (
            <ReleaseAll
              // A fresh selection whenever who is waiting changes (after a release).
              key={waiting.map((candidate) => candidate.user_id).join(",")}
              orgSlug={orgSlug}
              sittingId={sittingId}
              waiting={waiting}
              onChanged={onChanged}
              released={report.totals.decisions_released}
              total={report.totals.candidates}
            />
          ) : null}

          {report.sitting.mode === "exam" ? <CohortRanking orgSlug={orgSlug} sittingId={sittingId} /> : null}

          <section aria-label="Candidates" className="overflow-x-auto rounded-panel border border-b2b-border bg-b2b-surface">
            <table className="w-full min-w-[720px] border-collapse text-left">
              <thead>
                <tr className="border-b border-b2b-border text-osce-meta font-medium text-b2b-mid">
                  <th scope="col" className="px-4 py-3 font-medium">Candidate</th>
                  <th scope="col" className="px-4 py-3 font-medium">Score</th>
                  <th scope="col" className="px-4 py-3 font-medium">Outcome</th>
                  <th scope="col" className="px-4 py-3 font-medium">Status</th>
                  <th scope="col" className="px-4 py-3"><span className="sr-only">Actions</span></th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((candidate) => (
                  <CandidateCard
                    key={candidate.user_id}
                    orgSlug={orgSlug}
                    sittingId={sittingId}
                    candidate={candidate}
                    rating={report.rating ?? null}
                    hire={report.sitting.mode === "exam"}
                    onChanged={onChanged}
                  />
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </>
  );
}

/** Where the cohort stands: the recorded decisions, and who the markers still owe. */
function OutcomeTiles({
  candidates,
  awaitingMarking,
}: {
  candidates: CandidateReport[];
  awaitingMarking: number;
}) {
  const count = (outcome: string) =>
    candidates.filter((candidate) => candidate.decision?.assessment_outcome === outcome).length;
  const tiles = [
    { label: "Passed", value: count("pass") },
    { label: "Failed", value: count("fail") },
    { label: "Inconclusive", value: count("inconclusive") },
    { label: "Awaiting marking", value: awaitingMarking },
  ];
  return (
    <section aria-label="Outcomes" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {tiles.map((tile) => (
        <div key={tile.label} className={b2bTokens.b2bStatCard}>
          <span className={b2bTokens.b2bEyebrow}>{tile.label}</span>
          <span className={b2bTokens.b2bStatCardValue}>{tile.value}</span>
        </div>
      ))}
    </section>
  );
}

/**
 * Releasing signed-off decisions, several at once.
 *
 * Offers exactly what is signed off and not yet out, because that is the only
 * set the backend will accept anyway, each ticked by name so a lead can hold
 * one back (the retiring screen released a selection behind a
 * `window.confirm`). One request releases the lot; the backend runs each
 * through the single release, so each keeps its evidence check and its own
 * `candidate_result_released` email. A candidate whose marking moved since
 * sign-off is skipped by the backend and named here with the reason.
 */
function ReleaseAll({
  orgSlug,
  sittingId,
  waiting,
  onChanged,
  released: releasedTotal,
  total,
}: {
  orgSlug: string;
  sittingId: string;
  waiting: CandidateReport[];
  onChanged: () => void;
  /** Decisions already released, and candidates in all, for the tally beside the heading. */
  released: number;
  total: number;
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
    const entries = chosen.flatMap((candidate) =>
      candidate.trainee_id ? [{ traineeId: candidate.trainee_id, candidate }] : [],
    );
    const byTrainee = new Map(entries.map((entry) => [entry.traineeId, entry.candidate]));
    try {
      const result = await releaseDecisions(
        orgSlug,
        sittingId,
        entries.map(({ traineeId, candidate }) => ({
          traineeId,
          evidence: evidenceFor(candidate),
        })),
      );
      setReleased((result.released ?? []).length);
      setFailures(
        (result.skipped ?? []).map((skip) => {
          const candidate = byTrainee.get(skip.trainee_id);
          const name = candidate?.name ?? candidate?.email ?? "A candidate";
          return `${name}: ${releaseRefusal(skip.code)}`;
        }),
      );
    } catch (cause) {
      setFailures([errorMessage(cause instanceof Error ? cause : new Error(String(cause)))]);
    } finally {
      setBusy(false);
      onChanged();
    }
  }, [orgSlug, sittingId, chosen, onChanged]);

  return (
    <div className="space-y-3">
      <B2CHero
        eyebrow="Ready to release"
        title={`${waiting.length} signed off and not yet released`}
        action={
          <Button
            themeType="b2b"
            variant="commit"
            isLoading={busy}
            disabled={busy || chosen.length === 0}
            onClick={() => release()}
          >
            <HiOutlinePaperAirplane className="h-4 w-4 shrink-0" aria-hidden />
            {allPicked ? `Release all ${waiting.length}` : `Release ${chosen.length} selected`}
          </Button>
        }
        aside={
          <div className="text-right">
            <p className="font-mono text-[36px] leading-10 tabular-nums text-b2b-headline">
              {releasedTotal}{" "}
              <span className="text-osce-subheading text-b2b-mid">of {total}</span>
            </p>
            <p className="text-osce-meta text-b2b-mid">released</p>
          </div>
        }
      >
        Releasing lets each of them read their outcome. Untick anyone to hold back.
      </B2CHero>

      <Panel title="Candidates to release" padding="sm">
      <fieldset className="space-y-2">
        <legend className="sr-only">Candidates to release</legend>
        {waiting.length > 1 ? (
          <label className="flex items-center gap-2 text-osce-meta font-medium text-b2b-headline">
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
        <ul className="grid grid-cols-1 gap-1 sm:grid-cols-2">
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
      </Panel>

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
    </div>
  );
}
