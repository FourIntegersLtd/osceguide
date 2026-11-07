"use client";

import { boardCard, boardPad, boardRow, boardChip, boardAvatar, boardButtonSmall, type BoardChipTone, boardAlert } from "@/foundation/ui/boardKit";
import Link from "next/link";
import { useState } from "react";
import { b2bTokens as t } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { saveBlob } from "@/foundation/platform-client";
import { useSurface } from "@/capabilities";
import { can, useSession } from "@/foundation/session";
import { reviewPath } from "@/domains/assess/results/candidateNeighbours";
import { ratingLabel, type Rating } from "@/capabilities/feedback/rubric";
import { ratingVariant } from "@/domains/assess/results/reviewForm";
import { downloadCandidateResult, type CandidateReport, type StationReport } from "@/domains/assess/results/api";
import { candidateStage, owedMarking } from "@/domains/assess/results/candidateProgress";
import { CandidateDecision } from "@/domains/assess/results/CandidateDecision";

import {
  candidateName,
  formatScore,
  outcomeLabel,
  outcomeTone,
  workflowTone,
} from "@/domains/assess/results/support";

export const TONE_CHIP: Record<ReturnType<typeof outcomeTone>, BoardChipTone> = {
  success: "ok",
  danger: "live",
  warning: "warn",
  neutral: "neutral",
};
const STAGE_CHIP: Record<ReturnType<typeof workflowTone>, BoardChipTone> = {
  success: "ok",
  accent: "ok",
  neutral: "neutral",
};

/** One candidate as a row of the board's candidates card; "Open" shows their decision below the card. */
export function CandidateRow({
  orgSlug,
  sittingId,
  candidate,
  rating,
  open,
  onToggle,
}: {
  orgSlug: string;
  sittingId: string;
  candidate: CandidateReport;
  /** The sitting's rating (`SittingReport.rating`), which says how a review value is written. */
  rating: Rating | null;
  open: boolean;
  onToggle: () => void;
}) {
  const { session } = useSession();
  // Recording, signing off, releasing and the result PDF are institution admin routes.
  const mayDecide = can(session, "sign_off_results");
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const decision = candidate.decision;
  const resultReleased = candidate.trainee_id != null && decision?.released_at != null;
  const name = candidateName(candidate);

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

  return (
    <>
      <div className={boardRow}>
        <div aria-hidden className={boardAvatar}>
          {initials(name)}
        </div>
        <div className="flex-[1_1_220px]">
          <div className="font-medium">{name}</div>
          <div className={t.assessMeta}>
            {candidate.stations_marked} of {owedMarking(candidate.stations ?? []).length} stations marked
            {candidate.overall_rag !== null ? ` · overall ${ratingLabel(rating, candidate.overall_rag)}` : ""}
          </div>
        </div>
        <span className="w-[90px]">
          {formatScore(candidate.score, candidate.stations_marked > 0 ? "No score" : undefined)}
        </span>
        <span className="w-[110px]">
          {decision?.assessment_outcome ? (
            <span className={boardChip(TONE_CHIP[outcomeTone(decision.assessment_outcome)])}>
              {outcomeLabel(decision.assessment_outcome)}
            </span>
          ) : (
            <span className={t.assessMeta}>Not decided</span>
          )}
        </span>
        <span className="w-[100px]">
          <span className={boardChip(STAGE_CHIP[workflowTone(decision?.workflow_state)])}>
            {candidateStage(candidate)}
          </span>
        </span>
        <span className="flex w-[60px] items-center justify-end gap-2">
          {resultReleased && mayDecide ? (
            <button type="button" className={boardButtonSmall} disabled={downloading} onClick={() => downloadPdf()}>
              Result PDF
            </button>
          ) : null}
          <button
            type="button"
            className={boardButtonSmall}
            aria-expanded={open}
            aria-label={`${open ? "Close" : "Open"} ${name}`}
            onClick={onToggle}
          >
            {open ? "Close" : "Open"}
          </button>
        </span>
      </div>
      {downloadError ? (
        <div role="alert" className={`mx-5 mb-3 ${boardAlert("bad")}`}>
          {downloadError}
        </div>
      ) : null}
    </>
  );
}

/** The opened candidate: their stations and the decision, in the board's quiet-bordered card. */
export function CandidateDetail({
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
  rating: Rating | null;
  /** An exam-mode sitting, where the decision also records the recruitment outcome. */
  hire: boolean;
  onChanged: () => void;
}) {
  const { session } = useSession();
  const mayDecide = can(session, "sign_off_results");
  const stations = (candidate.stations ?? []).slice().sort((a, b) => a.slot_index - b.slot_index);
  const stationList = (
    <div className={boardCard}>
      <div className={`${boardRow} border-t-0`}>
        <div className={t.assessEyebrow}>Stations</div>
      </div>
      {stations.length === 0 ? (
        <p className={`${boardRow} m-0 ${t.assessMeta}`}>They have not sat anything yet.</p>
      ) : (
        stations.map((station) => (
          <StationRow key={station.slot_id} station={station} rating={rating} sittingId={sittingId} />
        ))
      )}
    </div>
  );
  return (
    <div className={`${boardPad} border-assess-select-border`} role="group" aria-label={`${candidateName(candidate)} decision`}>
      {mayDecide ? (
        <CandidateDecision
          orgSlug={orgSlug}
          sittingId={sittingId}
          candidate={candidate}
          hire={hire}
          stations={stationList}
          onChanged={onChanged}
        />
      ) : (
        <>
          <h2 className="text-base font-semibold leading-normal">{candidateName(candidate)}</h2>
          {stationList}
          <div className="flex flex-col gap-1">
            <h3 className="text-base font-semibold leading-normal">Supervisor view</h3>
            <p className={`m-0 ${t.assessMeta}`}>
              An institution administrator records, signs off and releases the decision. Its stage is shown in the row
              above.
            </p>
          </div>
        </>
      )}
    </div>
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
    <Link
      /* The sitting rides along so the review can step to the next candidate. */
      href={hrefFor(reviewPath(station.slot_id, station.attempt_id, sittingId))}
      className={`${boardRow} hover:bg-osce-surface-inset`}
    >
      <span className="flex-1">
        {station.station_title ?? "Station"}
        <div className={t.assessMeta}>{`${station.circuit_name} · ${station.slot_status.replace(/_/g, " ")}`}</div>
      </span>
      {station.overall_rag !== null ? (
        <span className={boardChip(TONE_CHIP[ratingVariant(rating, station.overall_rag)])}>
          {ratingLabel(rating, station.overall_rag)}
        </span>
      ) : (
        <span className={boardChip(station.marked ? "warn" : "neutral")}>
          {station.marked ? "Awaiting review" : station.absent ? "Absent" : "Not marked"}
        </span>
      )}
    </Link>
  );
}
