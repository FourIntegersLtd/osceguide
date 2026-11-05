"use client";

import { B2CGroupedRowLink, B2CGroupedSection, Badge, StepGuide } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readCircuitReview, type CircuitConsole } from "@/domains/assess/sessions/api";
import { markable, stationLabel } from "@/domains/assess/sessions/support";
import {
  circuitReviewSteps,
  stationsToMark,
  type ReviewStation,
} from "@/domains/assess/results/circuitReviewSteps";
import { slotReviewPath } from "@/domains/assess/results/support";

/** How many marked stations are listed before the rest fold into "N more marked stations". */
const MARKED_SHOWN = 1;

/**
 * What is left for a supervisor once a circuit ends: mark each station, share the circuit's
 * feedback, then the admin decides. Drawn from the console read the circuit page already holds.
 * Mount it above `CircuitFeedbackCard` when `circuit.ended_at` is set.
 */
export function CircuitReviewStep({
  data,
  orgSlug,
  circuitId,
}: {
  data: CircuitConsole;
  orgSlug: string;
  circuitId: string;
}) {
  const { hrefFor } = useSurface();
  // A failed read leaves the step at "Not published yet"; the feedback card below reports its own error.
  const review = useAsync((signal) => readCircuitReview(orgSlug, circuitId, signal), [orgSlug, circuitId]);
  const published = review.data?.state === "published";
  const stations: ReviewStation[] = (data.slots ?? [])
    .slice()
    .sort((a, b) => a.slot_index - b.slot_index)
    .map((slot) => ({
      slotId: slot.id,
      attemptId: slot.attempt_id ?? null,
      position: slot.slot_index + 1,
      title: stationLabel(slot),
      marked: slot.has_review,
      unmarked: !slot.has_review && markable(slot),
    }));
  const { steps, line } = circuitReviewSteps(stations, published);
  const ordered = stationsToMark(stations);
  const unmarked = ordered.filter((s) => s.unmarked);
  const marked = ordered.filter((s) => s.marked);
  const shown = [...unmarked, ...marked.slice(0, MARKED_SHOWN)];
  const hidden = marked.length - Math.min(marked.length, MARKED_SHOWN);

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
                <Badge variant={station.unmarked ? "warning" : "success"} dot>
                  {station.unmarked ? "Unmarked" : "Marked"}
                </Badge>
                <span className="ml-2 text-osce-meta font-medium text-b2b-headline">
                  {station.unmarked ? "Mark" : "Review"}
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
      <p className="text-osce-meta text-b2b-mid">
        Transcripts and automatic marking for each station open from its row. Only the supervisor named on this
        circuit can read what was said.
      </p>
    </section>
  );
}
