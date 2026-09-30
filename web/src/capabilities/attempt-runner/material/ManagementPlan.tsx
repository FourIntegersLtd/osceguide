"use client";

import type { AttemptReview } from "@/capabilities/attempt-runner/api";
import { StationComments } from "@/capabilities/community/StationComments";
import { b2cPageTitle } from "@/foundation/ui/productTokens";
import { AudienceSections, sectionsFor } from "./AudienceSections";

/**
 * The model answer once the consultation is over: the candidate's brief open,
 * then each examiner section as a collapsible panel, as the template lays them out.
 */
export function ManagementPlan({
  review,
}: {
  review: Pick<AttemptReview, "station_title" | "station_id" | "sections">;
}) {
  return (
    <div className="max-w-full select-none space-y-6 overflow-x-hidden sm:space-y-8">
      <h1 className={`${b2cPageTitle} my-4 text-center sm:my-6`}>{review.station_title}</h1>
      <div className="space-y-4">
        <AudienceSections sections={sectionsFor(review.sections, "candidate")} />
        <AudienceSections
          sections={sectionsFor(review.sections, "examiner")}
          variant="collapsible"
          emptyMessage="There is no model answer for this station."
        />
      </div>
      <StationComments stationId={review.station_id} />
    </div>
  );
}
