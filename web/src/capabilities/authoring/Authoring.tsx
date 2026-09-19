"use client";

import { useMemo, useState } from "react";
import { B2CSegmentedTabs, PageHeader } from "@/foundation/ui";
import { supportsProgrammes } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { StationsSection } from "@/capabilities/authoring/sections/StationsSection";
import { StationTemplatesSection } from "@/capabilities/authoring/sections/StationTemplatesSection";
import { FeedbackTemplatesSection } from "@/capabilities/authoring/sections/FeedbackTemplatesSection";
import { RubricsSection } from "@/capabilities/authoring/sections/RubricsSection";
import { ExamsSection } from "@/capabilities/authoring/sections/ExamsSection";
import { ProgrammesSection } from "@/capabilities/authoring/sections/ProgrammesSection";

type Section =
  | "stations"
  | "station-templates"
  | "feedback-templates"
  | "rubrics"
  | "exams"
  | "programmes";

/**
 * Writing the material an exam is made of — one screen, three arms.
 *
 * The retiring client reached these six sections through three route trees:
 * `/b2b/[orgSlug]/stations`, `/b2b/partner/[orgSlug]/{exams,stations,
 * templates}` and `/admin`. They rendered near-identical lists over endpoints
 * that differ only in their prefix, and a fix to one reached the others when
 * somebody remembered.
 *
 * Here there is one route and one implementation. What changes between an
 * institution, a partner and the staff console is the *base path* the api
 * layer prefixes — `useAuthoringScope` reads it off `SurfaceContext` — and,
 * for programmes, whether the backend serves the section at all.
 */
export function AuthoringHome() {
  const scope = useAuthoringScope();
  const [section, setSection] = useState<Section>("stations");

  const items = useMemo(
    () => TABS.filter((tab) => tab.id !== "programmes" || supportsProgrammes(scope)),
    [scope],
  );

  const active = items.some((tab) => tab.id === section) ? section : "stations";

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Authoring"
        description="Stations, templates, rubrics, exams and programmes."
      />

      <B2CSegmentedTabs
        items={items}
        value={active}
        onChange={setSection}
        aria-label="Authoring section"
      />

      {active === "stations" ? <StationsSection /> : null}
      {active === "station-templates" ? <StationTemplatesSection /> : null}
      {active === "feedback-templates" ? <FeedbackTemplatesSection /> : null}
      {active === "rubrics" ? <RubricsSection /> : null}
      {active === "exams" ? <ExamsSection /> : null}
      {active === "programmes" ? <ProgrammesSection /> : null}
    </div>
  );
}

const TABS: { id: Section; label: string }[] = [
  { id: "stations", label: "Stations" },
  { id: "station-templates", label: "Station templates" },
  { id: "feedback-templates", label: "Feedback templates" },
  { id: "rubrics", label: "Rubrics" },
  { id: "exams", label: "Exams" },
  { id: "programmes", label: "Programmes" },
];
