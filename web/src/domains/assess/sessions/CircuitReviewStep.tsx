"use client";

import { B2CGroupedRowLink, B2CGroupedSection, Badge, StepGuide } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import { markable, orderedSlots, slotReviewPath, stationLabel } from "@/domains/assess/sessions/support";
import { circuitReviewSteps, stationsToMark, type ReviewStation } from "@/domains/assess/sessions/circuitReviewSteps";

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
    state: slot.has_review ? "marked" : markable(slot) ? "unmarked" : "not_sat",
  }));
  const { steps, line } = circuitReviewSteps(stations, published);
  const ordered = stationsToMark(stations);
  const unmarked = ordered.filter((s) => s.state === "unmarked");
  const marked = ordered.filter((s) => s.state === "marked");
  // Unmarked stations lead; one marked station is shown and the rest fold into a count.
  const shown = [...unmarked, ...marked.slice(0, 1)];
  const hidden = marked.length - Math.min(marked.length, 1);

  return (
    <section aria-label="Marking and review" className="flex flex-col gap-4">
      <StepGuide steps={steps} line={line} />
      <B2CGroupedSection eyebrow="Stations to mark">
        {shown.map((station) => (
          <B2CGroupedRowLink
            key={station.slotId}
            href={hrefFor(slotReviewPath(station))}
            title={`${station.position} · ${station.title}`}
            trailing={
              <>
                <Badge variant={station.state === "unmarked" ? "warning" : "success"} dot>
                  {station.state === "unmarked" ? "Unmarked" : "Marked"}
                </Badge>
                <span className="ml-2 text-osce-meta font-medium text-b2b-headline">
                  {station.state === "unmarked" ? "Mark" : "Review"}
                </span>
              </>
            }
          />
        ))}
        {hidden > 0 ? (
          <p className="px-4 py-3 text-osce-meta text-b2b-mid">
            {hidden} more marked station{hidden === 1 ? "" : "s"}
          </p>
        ) : null}
      </B2CGroupedSection>
      <h3 className="text-osce-body font-semibold text-b2b-headline">The record</h3>
      <p className="-mt-2 text-osce-meta text-b2b-mid">
        Transcripts and automatic marking for each station open from its row. Only the supervisor named on this
        circuit can read what was said.
      </p>
    </section>
  );
}
