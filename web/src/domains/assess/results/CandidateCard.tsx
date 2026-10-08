"use client";

import { useState } from "react";
import { LuClipboardCheck } from "react-icons/lu";
import { Alert, B2CGroupedRowLink, B2CGroupedSection, Badge, Button, b2bTokens, FoldSection } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { saveBlob } from "@/foundation/platform-client";
import { useSurface } from "@/capabilities";
import { can, useSession } from "@/foundation/session";
import { reviewPath } from "@/domains/assess/results/candidateNeighbours";
import { ratingLabel, type Rating } from "@/capabilities/feedback/rubric";
import { ratingVariant } from "@/domains/assess/results/reviewForm";
import { downloadCandidateResult, type CandidateReport, type StationReport } from "@/domains/assess/results/api";
import { candidateStage } from "@/domains/assess/results/candidateProgress";
import { CandidateDecision } from "@/domains/assess/results/CandidateDecision";
import {
  candidateName,
  formatScore,
  outcomeLabel,
  outcomeTone,
  workflowTone,
} from "@/domains/assess/results/support";

/**
 * One candidate as a table row, with their stations and decision in a row beneath it.
 *
 * The retiring client made this a separate page per candidate — a "candidate
 * pack" — and a lead reviewing a cohort of twelve walked twelve routes and
 * back. The report carries everything already, so opening one is a disclosure
 * rather than a navigation.
 */
export function CandidateCard({
  orgSlug,
  sittingId,
  candidate,
  rating,
  hire,
  onChanged,
}: {
  orgSlug: string;
  sittingId: string;
  candidate: CandidateReport;
  /** The sitting's rating (`SittingReport.rating`), which says how a review value is written. */
  rating: Rating | null;
  /** An exam-mode sitting, where the decision also records the recruitment outcome. */
  hire: boolean;
  onChanged: () => void;
}) {
  const { session } = useSession();
  // Recording, signing off, releasing and the result PDF are institution admin routes.
  const mayDecide = can(session, "sign_off_results");
  const [open, setOpen] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const decision = candidate.decision;
  const stations = candidate.stations ?? [];
  const resultReleased = candidate.trainee_id != null && decision?.released_at != null;

  async function downloadPdf() {
    if (!candidate.trainee_id) return;
    setDownloading(true);
    setDownloadError(null);
    try {
      const file = await downloadCandidateResult(orgSlug, sittingId, candidate.trainee_id);
      saveBlob(file.blob, file.filename);
    } catch (cause) {
      setDownloadError(errorMessage(cause));
    } finally {
      setDownloading(false);
    }
  }

  const name = candidateName(candidate);

  return (
    <>
      <tr className="border-b border-b2b-border last:border-b-0">
        <td className="px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <span
              aria-hidden
              className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full bg-canvas text-[11.5px] text-b2b-mid"
            >
              {initials(name)}
            </span>
            <div className="min-w-0">
              <p className={b2bTokens.b2bGroupedRowTitle}>{name}</p>
              <p className={b2bTokens.b2bGroupedRowSubtitle}>
                {candidate.stations_marked} of {stations.filter((station) => !station.absent).length} stations marked
                {candidate.overall_rag !== null ? ` · overall ${ratingLabel(rating, candidate.overall_rag)}` : ""}
              </p>
            </div>
          </div>
        </td>
        <td className="px-4 py-3 font-mono text-osce-body tabular-nums text-b2b-headline">
          {formatScore(candidate.score, candidate.stations_marked > 0 ? "No automatic score" : undefined)}
        </td>
        <td className="px-4 py-3">
          {decision?.assessment_outcome ? (
            <Badge variant={outcomeTone(decision.assessment_outcome)} dot>
              {outcomeLabel(decision.assessment_outcome)}
            </Badge>
          ) : (
            <span className="text-osce-meta text-b2b-mid">Not decided</span>
          )}
        </td>
        <td className="px-4 py-3">
          <Badge variant={workflowTone(decision?.workflow_state)} dot>
            {candidateStage(candidate)}
          </Badge>
        </td>
        <td className="px-4 py-3">
          <div className="flex items-center justify-end gap-2">
            {resultReleased && mayDecide ? (
              <Button
                themeType="b2b"
                variant="ghost"
                size="sm"
                isLoading={downloading}
                disabled={downloading}
                onClick={() => downloadPdf()}
              >
                Result PDF
              </Button>
            ) : null}
            <Button
              themeType="b2b"
              variant="secondary"
              size="sm"
              aria-expanded={open}
              aria-label={`${open ? "Close" : "Open"} ${name}`}
              onClick={() => setOpen((value) => !value)}
            >
              {open ? "Close" : "Open"}
            </Button>
          </div>
        </td>
      </tr>
      {downloadError ? (
        <tr>
          <td colSpan={5} className="px-4 pb-3">
            <Alert tone="danger">{downloadError}</Alert>
          </td>
        </tr>
      ) : null}
      {open ? (
        <tr className="border-b border-b2b-border bg-canvas/40 last:border-b-0">
          <td colSpan={5} className="space-y-5 p-4 sm:p-5">
            <B2CGroupedSection eyebrow="Stations">
              {stations.length === 0 ? (
                <p className="px-4 py-3 text-osce-meta text-b2b-mid">They have not sat anything yet.</p>
              ) : (
                stations
                  .slice()
                  .sort((a, b) => a.slot_index - b.slot_index)
                  .map((station) => (
                    <StationRow key={station.slot_id} station={station} rating={rating} sittingId={sittingId} />
                  ))
              )}
            </B2CGroupedSection>

            <FoldSection title="The decision">
              {mayDecide ? (
                <CandidateDecision
                  orgSlug={orgSlug}
                  sittingId={sittingId}
                  candidate={candidate}
                  hire={hire}
                  onChanged={onChanged}
                />
              ) : (
                <p className="text-osce-body text-b2b-mid">
                  An institution administrator records, signs off and releases the decision. Its stage is shown in the
                  row above.
                </p>
              )}
            </FoldSection>
          </td>
        </tr>
      ) : null}
    </>
  );
}

/** Up to two capital letters from a name, skipping a leading title. */
function initials(name: string): string {
  const words = name.replace(/^(dr|mr|mrs|ms|prof)\.?\s+/i, "").split(/\s+/).filter(Boolean);
  return ((words[0]?.[0] ?? "?") + (words.length > 1 ? (words.at(-1)?.[0] ?? "") : "")).toUpperCase();
}

function StationRow({
  station,
  rating,
  sittingId,
}: {
  station: StationReport;
  rating: Rating | null;
  sittingId: string;
}) {
  const { hrefFor } = useSurface();

  return (
    <B2CGroupedRowLink
      /* The sitting rides along so the review can step to the next candidate. */
      href={hrefFor(reviewPath(station.slot_id, station.attempt_id, sittingId))}
      icon={LuClipboardCheck}
      title={station.station_title ?? "Station"}
      meta={`${station.circuit_name} · ${station.slot_status.replace(/_/g, " ")}`}
      trailing={
        station.overall_rag !== null ? (
          <Badge variant={ratingVariant(rating, station.overall_rag)} dot>
            {ratingLabel(rating, station.overall_rag)}
          </Badge>
        ) : (
          <Badge variant="neutral" dot>
            {station.marked ? "Awaiting review" : station.absent ? "Absent" : "Not marked"}
          </Badge>
        )
      }
    />
  );
}
