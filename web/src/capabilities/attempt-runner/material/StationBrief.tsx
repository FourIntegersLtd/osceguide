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
  const sections = sectionsFor(brief.sections, "candidate");
  // The legacy screens headed the panel with the section's own name — SCA's
  // read "Doctor Information" — so a lone section lends the shell its title.
  const shellTitle = sections.length === 1 ? sections[0]!.title : "Station information";
  return (
    <DoctorInfoShell embedded={embedded} title={shellTitle || "Station information"}>
      <AudienceSections
        sections={sections}
        variant="brief"
        emptyMessage="There is no written brief for this station."
      />
    </DoctorInfoShell>
  );
}
