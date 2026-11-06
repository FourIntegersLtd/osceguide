"use client";

import { ButtonLink } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { reviewPath, type CandidateSteps } from "@/domains/assess/results/candidateNeighbours";

/**
 * Previous and next candidate on the same station.
 *
 * Read off the sitting's report rather than asked of a route of its own. It is
 * a convenience beside the form, so while it loads there is nothing to show,
 * and a failure says so without taking the form down with it.
 */
export function CandidateStepper({ steps, sittingId }: { steps: CandidateSteps; sittingId: string }) {
  const { hrefFor } = useSurface();
  if (steps.total < 2) return null;
  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <span className="text-assess-meta tabular-nums text-osce-ink-500">
        Candidate {steps.position} of {steps.total}
      </span>
      {steps.previous ? (
        <ButtonLink
          href={hrefFor(reviewPath(steps.previous.slotId, steps.previous.attemptId, sittingId))}
          themeType="b2b"
          variant="secondary"
          size="sm"
        >
          ‹ Previous candidate
        </ButtonLink>
      ) : null}
      {steps.next ? (
        <ButtonLink
          href={hrefFor(reviewPath(steps.next.slotId, steps.next.attemptId, sittingId))}
          themeType="b2b"
          variant="secondary"
          size="sm"
        >
          Next candidate ›
        </ButtonLink>
      ) : null}
    </div>
  );
}
