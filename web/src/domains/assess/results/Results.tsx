"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { AsyncBoundary, b2bTokens as t } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { saveBlob } from "@/foundation/platform-client";
import { downloadSittingResults, downloadSittingShortlist, readSittingReport } from "@/domains/assess/results/api";
import type { CandidateReport, SittingReport } from "@/domains/assess/results/api";
import { CandidateDetail, CandidateRow } from "@/domains/assess/results/CandidateCard";
import { ReleaseAll } from "@/domains/assess/results/ReleaseAll";
import { CandidateRanking } from "@/domains/assess/results/CandidateRanking";
import { CohortRanking } from "@/domains/assess/results/CohortRanking";
import { countsFromReport, sittingNext, sittingSteps, type SittingStepsInput } from "@/domains/assess/sittingSteps";
import { can, useSession } from "@/foundation/session";
import { useAssessWords } from "@/domains/assess/useAssessWords";
import { releasable, signOffLeft } from "@/domains/assess/results/support";
import { boardCard, boardHeadRow, boardPad, boardTile , boardBtn, boardAlert } from "@/foundation/ui/boardKit";
import { boardTile6, boardTileNumber } from "@/domains/assess/results/resultsChrome";
import { boardRailStep } from "@/domains/assess/chrome";

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
    <section aria-label="Results" className={t.assessPage}>
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
    </section>
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
  const { session } = useSession();
  const progress: SittingStepsInput = {
    scheduledFor: report.sitting.scheduled_for ?? null,
    circuits: null,
    counts: countsFromReport(report),
    training: report.sitting.mode !== "exam",
    can: { schedule: can(session, "schedule_sittings"), signOff: can(session, "sign_off_results") },
  };
  const candidates = report.candidates ?? [];
  // Only someone who may release is offered the list to release from; everyone else reads the steps.
  const waiting = progress.can.signOff && !progress.training ? candidates.filter(releasable) : [];
  const { total, left } = signOffLeft(candidates);
  const w = useAssessWords();
  const signOffNote =
    progress.can.signOff && !progress.training && left > 0
      ? `Sign off needs a decision for all ${total} ${w.trainees}. ${left} ${left === 1 ? "is" : "are"} left.`
      : null;
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  // One candidate's decision is open at a time, below the table, as on the board.
  const [openId, setOpenId] = useState<string | null>(null);
  const opened = candidates.find((candidate) => candidate.user_id === openId) ?? null;

  const downloadCsv = useCallback(async (download: typeof downloadSittingResults = downloadSittingResults) => {
    setDownloading(true);
    setDownloadError(null);
    try {
      const file = await download(orgSlug, sittingId);
      saveBlob(file.blob, file.filename);
    } catch (cause) {
      setDownloadError(errorMessage(cause));
    } finally {
      setDownloading(false);
    }
  }, [orgSlug, sittingId]);

  const steps = sittingSteps(progress);
  const nowId = steps.find((step) => step.state !== "done")?.id;

  return (
    <>
      <div>
        <Link href={hrefFor(`/sittings/${sittingId}`)} className="text-assess-label text-osce-accent">
          ‹ Sitting
        </Link>
      </div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className={t.assessEyebrow}>{report.sitting.name}</div>
          <h1 className={t.assessTitle}>Results</h1>
          <p className={t.assessDesc}>
            {`${report.totals.stations_marked} of ${report.totals.stations} stations marked · ${report.totals.decisions_released} of ${report.totals.candidates} released`}
          </p>
        </div>
        {can(session, "export_results") ? (
          <div className="flex flex-wrap items-center gap-2.5">
            <button type="button" className={boardBtn()} disabled={downloading} onClick={() => downloadCsv()}>
              Download CSV
            </button>
            {progress.training ? null : (
              <button type="button" className={boardBtn()} disabled={downloading} onClick={() => downloadCsv(downloadSittingShortlist)}>
                Download shortlist
              </button>
            )}
          </div>
        ) : null}
      </div>
      {downloadError ? <div role="alert" className={boardAlert("bad")}>{downloadError}</div> : null}

      <OutcomeTiles candidates={candidates} awaitingMarking={report.totals.awaiting_marking} />
      {candidates.length === 0 ? (
        <div className={boardPad}>
          <h2 className="text-base font-semibold leading-normal">Nobody has sat this yet.</h2>
        </div>
      ) : (
        <>
          <div className={boardPad}>
            <div className="flex flex-wrap gap-2">
              {steps.map((step) => (
                <div key={step.id} className={boardRailStep(step.state, step.id === nowId)}>
                  <b className="block text-assess-label font-medium">{step.label}</b>
                  {step.note}
                </div>
              ))}
            </div>
            <div className="text-assess-label">{sittingNext(progress).line}</div>
            {signOffNote ? <div className={t.assessMeta}>{signOffNote}</div> : null}
            {waiting.length > 0 ? (
              <ReleaseAll
                orgSlug={orgSlug}
                sittingId={sittingId}
                waiting={waiting}
                onChanged={onChanged}
                progress={progress}
              />
            ) : null}
          </div>

          {w.hiring && report.sitting.mode === "exam" ? (
            <CandidateRanking candidates={candidates} openId={openId} onOpen={(id) => {
                setOpenId(id);
                requestAnimationFrame(() => document.getElementById("candidate-detail")?.scrollIntoView({ block: "start" }));
              }} />
          ) : null}
          {report.sitting.mode === "exam" ? <CohortRanking orgSlug={orgSlug} sittingId={sittingId} numbered={!w.hiring} /> : null}

          <section aria-label="Candidates" className={`${boardCard} overflow-hidden`}>
            <div className={boardHeadRow}>
              <span className="w-8" />
              <span className="flex-[1_1_220px]">Candidate</span>
              <span className="w-[90px]">Score</span>
              <span className="w-[110px]">Outcome</span>
              <span className="w-[100px]">Status</span>
              <span className="w-[60px]" />
            </div>
            {candidates.map((candidate) => (
              <CandidateRow
                key={candidate.user_id}
                orgSlug={orgSlug}
                sittingId={sittingId}
                candidate={candidate}
                rating={report.rating ?? null}
                open={candidate.user_id === openId}
                onToggle={() => setOpenId(candidate.user_id === openId ? null : candidate.user_id)}
              />
            ))}
          </section>
          {opened ? (
            <div id="candidate-detail" tabIndex={-1} className="scroll-mt-4 outline-none">
            <CandidateDetail
              key={opened.user_id}
              orgSlug={orgSlug}
              sittingId={sittingId}
              candidate={opened}
              rating={report.rating ?? null}
              hire={report.sitting.mode === "exam"}
              onChanged={onChanged}
            />
            </div>
          ) : null}
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
    { label: "Withheld", value: count("withheld") },
    {
      label: "Undecided",
      value: candidates.filter((candidate) => !candidate.decision?.assessment_outcome).length,
    },
    { label: "Awaiting marking", value: awaitingMarking },
  ];
  return (
    <div role="group" aria-label="Outcomes" className={boardTile6}>
      {tiles.map((tile) => (
        <div key={tile.label} className={boardTile}>
          {tile.label}
          <b className={boardTileNumber}>{tile.value}</b>
        </div>
      ))}
    </div>
  );
}
