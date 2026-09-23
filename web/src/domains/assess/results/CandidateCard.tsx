"use client";

import Link from "next/link";
import { useState } from "react";
import { HiChevronDown, HiChevronRight } from "react-icons/hi2";
import { Badge, b2bTokens } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { RAG_LABEL, type Rag } from "@/capabilities/feedback";
import type { CandidateReport, StationReport } from "@/domains/assess/results/api";
import { CandidateDecision } from "@/domains/assess/results/CandidateDecision";
import {
  candidateName,
  outcomeTone,
  workflowLabel,
  workflowTone,
} from "@/domains/assess/results/support";

/**
 * One candidate, with their stations and their decision behind a disclosure.
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
  onChanged,
}: {
  orgSlug: string;
  sittingId: string;
  candidate: CandidateReport;
  onChanged: () => void;
}) {
  const [open, setOpen] = useState(false);
  const decision = candidate.decision;
  const stations = candidate.stations ?? [];

  return (
    <div className="overflow-hidden rounded-lg border border-b2b-border bg-white">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-b2b-cream/60 sm:px-5"
      >
        {open ? (
          <HiChevronDown className="h-4 w-4 shrink-0 text-b2b-icon" aria-hidden />
        ) : (
          <HiChevronRight className="h-4 w-4 shrink-0 text-b2b-icon" aria-hidden />
        )}
        <div className="min-w-0 flex-1">
          <p className={b2bTokens.b2bGroupedRowTitle}>{candidateName(candidate)}</p>
          <p className={b2bTokens.b2bGroupedRowSubtitle}>
            {candidate.stations_marked} of {stations.length} stations marked
            {candidate.overall_rag ? ` · overall ${RAG_LABEL[candidate.overall_rag as Rag] ?? candidate.overall_rag}` : ""}
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
          {decision?.assessment_outcome ? (
            <Badge variant={outcomeTone(decision.assessment_outcome)}>
              {decision.assessment_outcome}
            </Badge>
          ) : null}
          <Badge variant={workflowTone(decision?.workflow_state)}>
            {workflowLabel(decision?.workflow_state)}
          </Badge>
        </div>
      </button>

      {open ? (
        <div className="space-y-5 border-t border-b2b-border p-4 sm:p-5">
          <section className="space-y-2">
            <h3 className={b2bTokens.b2bSectionTitle}>Stations</h3>
            {stations.length === 0 ? (
              <p className="text-osce-caption text-b2b-mid">They have not sat anything yet.</p>
            ) : (
              <ul className="divide-y divide-b2b-border rounded-lg border border-b2b-border">
                {stations
                  .slice()
                  .sort((a, b) => a.slot_index - b.slot_index)
                  .map((station) => (
                    <StationRow key={station.slot_id} station={station} />
                  ))}
              </ul>
            )}
          </section>

          <section className="space-y-2">
            <h3 className={b2bTokens.b2bSectionTitle}>The decision</h3>
            <CandidateDecision
              orgSlug={orgSlug}
              sittingId={sittingId}
              candidate={candidate}
              onChanged={onChanged}
            />
          </section>
        </div>
      ) : null}
    </div>
  );
}

function StationRow({ station }: { station: StationReport }) {
  const { hrefFor } = useSurface();

  return (
    <li className="flex flex-wrap items-center justify-between gap-2 px-3 py-2.5">
      <div className="min-w-0">
        <p className="truncate text-osce-caption font-medium text-b2b-headline">
          {station.station_title ?? "Station"}
        </p>
        <p className="truncate text-osce-caption text-b2b-mid">
          {station.circuit_name} · {station.slot_status.replace(/_/g, " ")}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {station.overall_rag ? (
          <Badge variant={ragTone(station.overall_rag)}>
            {RAG_LABEL[station.overall_rag as Rag] ?? station.overall_rag}
          </Badge>
        ) : (
          <Badge variant="neutral">{station.marked ? "Awaiting review" : "Not marked"}</Badge>
        )}
        <Link
          href={hrefFor(
            `/slots/${station.slot_id}/review${station.attempt_id ? `?attempt=${station.attempt_id}` : ""}`,
          )}
          className={b2bTokens.b2bLink}
        >
          Review
        </Link>
      </div>
    </li>
  );
}

function ragTone(rag: string): "success" | "warning" | "danger" | "neutral" {
  if (rag === "G") return "success";
  if (rag === "A") return "warning";
  if (rag === "R") return "danger";
  return "neutral";
}
