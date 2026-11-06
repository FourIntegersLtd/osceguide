"use client";

import Link from "next/link";
import { StepGuide } from "@/foundation/ui";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { boardCard, boardPad, boardRow, boardChip, boardButtonSmall } from "@/foundation/ui/boardKit";
import { useSurface } from "@/capabilities";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import { markable, orderedSlots, slotReviewPath, stationLabel } from "@/domains/assess/sessions/support";
import { circuitReviewSteps, stationsToMark, type ReviewStation } from "@/domains/assess/sessions/circuitReviewSteps";
import { cardTitle } from "@/domains/assess/chrome";

/**
 * What is left for a supervisor once a circuit ends: mark each station, share the circuit's
 * feedback, then the admin decides. Drawn from the console read the circuit page already holds;
 * `published` comes from the runner's one read of the circuit review.
 */
export function CircuitReviewStep({ data, published }: { data: CircuitConsole; published: boolean }) {
  const { hrefFor } = useSurface();
  const stations: ReviewStation[] = orderedSlots(data).map((slot) => ({
    slotId: slot.id,
    attemptId: slot.attempt_id ?? null,
    position: slot.slot_index + 1,
    title: stationLabel(slot),
    state: slot.marked ? "marked" : markable(slot) ? "unmarked" : "not_sat",
  }));
  const { steps, line } = circuitReviewSteps(stations, published);
  const ordered = stationsToMark(stations);
  const unmarked = ordered.filter((s) => s.state === "unmarked");
  const marked = ordered.filter((s) => s.state === "marked");
  // Unmarked stations lead; one marked station is shown and the rest fold into a count.
  const shown = [...unmarked, ...marked.slice(0, 1)];
  const hidden = marked.length - Math.min(marked.length, 1);

  return (
    <section id="circuit-review" aria-label="Marking and review" className="flex flex-col gap-5">
      <StepGuide steps={steps} line={line} />
      <div className={boardCard}>
        <div className={`${boardRow} border-t-0`}>
          <h2 className={cardTitle}>Stations to mark</h2>
        </div>
        {shown.map((station) => (
          <Link key={station.slotId} href={hrefFor(slotReviewPath(station))} className={boardRow}>
            <span className="flex-1">{`${station.position} · ${station.title}`}</span>
            <span className={boardChip(station.state === "unmarked" ? "warn" : "ok")}>
              {station.state === "unmarked" ? "Unmarked" : "Marked"}
            </span>
            <span className={boardButtonSmall}>{station.state === "unmarked" ? "Mark" : "Review"}</span>
          </Link>
        ))}
        {hidden > 0 ? (
          <div className={`${boardRow} ${assessMeta}`}>
            {hidden} more marked station{hidden === 1 ? "" : "s"}
          </div>
        ) : null}
      </div>
      <div className={boardPad}>
        <h2 className={cardTitle}>The record</h2>
        <p className={assessMeta}>
          Transcripts and automatic marking for each station open from its row. Only the supervisor named on this
          circuit can read what was said.
        </p>
      </div>
    </section>
  );
}
