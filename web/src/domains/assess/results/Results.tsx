"use client";

import { useCallback, useState } from "react";
import { Alert, AsyncBoundary, B2CPageHeader, Button, EmptyState, StatGrid, StatTile, StepGuide } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { saveBlob } from "@/foundation/platform-client";
import { downloadSittingResults, readSittingReport } from "@/domains/assess/results/api";
import type { CandidateReport, SittingReport } from "@/domains/assess/results/api";
import { CandidateCard } from "@/domains/assess/results/CandidateCard";
import { ReleaseAll } from "@/domains/assess/results/ReleaseAll";
import { CohortRanking } from "@/domains/assess/results/CohortRanking";
import { countsFromReport, sittingNext, sittingSteps, type SittingStepsInput } from "@/domains/assess/sittingSteps";
import { can, useSession } from "@/foundation/session";
import { releasable } from "@/domains/assess/results/support";

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
          can(session, "export_results") ? (
            <Button
              themeType="b2b"
              variant="secondary"
              isLoading={downloading}
              disabled={downloading}
              onClick={() => downloadCsv()}
            >
              Download CSV
            </Button>
          ) : undefined
        }
      />
      {downloadError ? <Alert tone="danger">{downloadError}</Alert> : null}

      <h2 className="text-osce-body font-medium text-b2b-headline">Outcomes</h2>
      <OutcomeTiles candidates={candidates} awaitingMarking={report.totals.awaiting_marking} />
      {candidates.length === 0 ? (
        <EmptyState title="Nobody has sat this yet." />
      ) : (
        <>

          {waiting.length === 0 ? <StepGuide steps={sittingSteps(progress)} line={sittingNext(progress).line} /> : null}
          {waiting.length > 0 ? (
            <ReleaseAll
              orgSlug={orgSlug}
              sittingId={sittingId}
              waiting={waiting}
              onChanged={onChanged}
              progress={progress}
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
    { label: "Withheld", value: count("withheld") },
    {
      label: "Undecided",
      value: candidates.filter((candidate) => !candidate.decision?.assessment_outcome).length,
    },
    { label: "Awaiting marking", value: awaitingMarking },
  ];
  return (
    <StatGrid label="Outcomes" columns={6}>
      {tiles.map((tile) => (
        <StatTile key={tile.label} label={tile.label} value={tile.value} />
      ))}
    </StatGrid>
  );
}
