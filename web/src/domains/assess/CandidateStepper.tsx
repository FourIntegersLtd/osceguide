"use client";

import { ButtonLink } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readSittingReport } from "@/domains/assess/results";
import { candidateSteps, reviewPath } from "@/domains/assess/results/candidateNeighbours";

/**
 * Previous and next candidate on the same station.
 *
 * Read off the sitting's report rather than asked of a route of its own. It is
 * a convenience beside the form, so while it loads there is nothing to show,
 * and a failure says so without taking the form down with it.
 */
export function CandidateStepper({ orgSlug, sittingId, slotId }: { orgSlug: string; sittingId: string; slotId: string }) {
  const { hrefFor } = useSurface();
  const report = useAsync((signal) => readSittingReport(orgSlug, sittingId, signal), [orgSlug, sittingId]);

  if (report.error) return <p className="text-osce-meta text-b2b-mid">Could not load the other candidates.</p>;
  const steps = report.data ? candidateSteps(report.data.candidates ?? [], slotId) : null;
  if (!steps || steps.total < 2) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-osce-meta tabular-nums text-b2b-mid">
        Candidate {steps.position} of {steps.total}
      </span>
      {steps.previous ? (
        <ButtonLink
          href={hrefFor(reviewPath(steps.previous.slotId, steps.previous.attemptId, sittingId))}
          themeType="b2b"
          variant="secondary"
          size="sm"
        >
          Previous
        </ButtonLink>
      ) : null}
      {steps.next ? (
        <ButtonLink
          href={hrefFor(reviewPath(steps.next.slotId, steps.next.attemptId, sittingId))}
          themeType="b2b"
          variant="secondary"
          size="sm"
        >
          Next candidate
        </ButtonLink>
      ) : null}
    </div>
  );
}
