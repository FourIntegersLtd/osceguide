"use client";

import { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { B2CSegmentedTabs, B2CPageHeader, PlatformTabbedScreen } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { supportsProgrammes } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import {
  authoringTabItems,
  parseAuthoringSection,
  type AuthoringSection,
} from "@/capabilities/authoring/sections";
import { StationsSection } from "@/capabilities/authoring/sections/StationsSection";
import { StationTemplatesSection } from "@/capabilities/authoring/sections/StationTemplatesSection";
import { RubricsSection } from "@/capabilities/authoring/sections/RubricsSection";
import { ExamsSection } from "@/capabilities/authoring/sections/ExamsSection";
import { ProgrammesSection } from "@/capabilities/authoring/sections/ProgrammesSection";

const DEFAULT_SECTION: AuthoringSection = "stations";

export function AuthoringHome({ section: sectionSlug }: { section?: string }) {
  const scope = useAuthoringScope();
  const { surface, hrefFor } = useSurface();
  const router = useRouter();

  const items = useMemo(
    () => authoringTabItems(supportsProgrammes(scope)),
    [scope],
  );

  const parsed = parseAuthoringSection(sectionSlug);
  const active =
    parsed && items.some((item) => item.id === parsed) ? parsed : DEFAULT_SECTION;

  useEffect(() => {
    if (!sectionSlug) {
      router.replace(`${hrefFor("/authoring")}/${DEFAULT_SECTION}`);
      return;
    }
    if (!parsed) {
      router.replace(`${hrefFor("/authoring")}/${DEFAULT_SECTION}`);
    }
  }, [sectionSlug, parsed, router, hrefFor]);

  const onTabChange = (id: AuthoringSection) => {
    router.push(`${hrefFor("/authoring")}/${id}`);
  };

  const panel = (
    <div id={`authoring-panel-${active}`} role="tabpanel">
      {active === "stations" ? <StationsSection /> : null}
      {active === "station-templates" ? <StationTemplatesSection /> : null}
      {active === "rubrics" ? <RubricsSection /> : null}
      {active === "exams" ? <ExamsSection /> : null}
      {active === "programmes" ? <ProgrammesSection /> : null}
    </div>
  );

  if (surface === "platform") {
    return (
      <PlatformTabbedScreen
        title="Authoring"
        description="Stations, templates, rubrics, exams and programmes."
        tabs={items}
        value={active}
        onChange={onTabChange}
        ariaLabel="Authoring section"
      >
        {panel}
      </PlatformTabbedScreen>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader title="Authoring" subtitle="Stations, templates, rubrics, exams and programmes." />
      <B2CSegmentedTabs
        items={items}
        value={active}
        onChange={onTabChange}
        aria-label="Authoring section"
      />
      {panel}
    </div>
  );
}
