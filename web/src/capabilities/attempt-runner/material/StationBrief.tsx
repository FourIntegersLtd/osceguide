"use client";

import type { AttemptBrief } from "@/capabilities/attempt-runner/api";
import { DoctorInfoShell } from "@/capabilities/attempt-runner/material/DoctorInfoLayout";
import { AudienceSections, sectionsFor } from "./AudienceSections";

/**
 * What the candidate reads before the patient is called, laid out by the
 * station's template: every exam, Ortho's radiographs and ward lists included.
 *
 * `embedded` is the consultation screen's right-hand column, where the brief
 * stays visible while the candidate talks; standalone is the reading period.
 */
export function StationBrief({
  brief,
  embedded = false,
}: {
  brief: Pick<AttemptBrief, "sections">;
  embedded?: boolean;
}) {
  return (
    <DoctorInfoShell embedded={embedded} title="Station information">
      <AudienceSections
        sections={sectionsFor(brief.sections, "candidate")}
        emptyMessage="There is no written brief for this station."
      />
    </DoctorInfoShell>
  );
}
