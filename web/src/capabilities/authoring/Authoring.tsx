"use client";

import { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { PlatformTabbedScreen, b2bTokens as t, cn } from "@/foundation/ui";
import { boardMeta, boardStack } from "@/capabilities/authoring/parts/boardUi";
import { boardCardClipped, boardTab, boardTabs, boardButtonSmall } from "@/foundation/ui/boardKit";
import { useSurface } from "@/capabilities";
import { supportsProgrammes } from "@/capabilities/authoring/api";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import {
  authoringTabItems,
  DEFAULT_AUTHORING_SECTION,
  parseAuthoringSection,
} from "@/capabilities/authoring/sections";
import { StationsSection } from "@/capabilities/authoring/sections/StationsSection";
import { StationTemplatesSection } from "@/capabilities/authoring/sections/StationTemplatesSection";
import { RubricsSection } from "@/capabilities/authoring/sections/RubricsSection";
import { ExamsSection } from "@/capabilities/authoring/sections/ExamsSection";
import { ProgrammesSection } from "@/capabilities/authoring/sections/ProgrammesSection";



const boardStateCard = `${boardCardClipped} flex flex-col gap-[14px] p-5`;
const ALERT = "flex flex-wrap items-center gap-2 rounded-board bg-osce-danger-bg px-3.5 py-3 text-assess-label leading-normal text-osce-danger-text";
const STATES_ID = "states";
const STATES_LABEL = "Empty and read-only states";
/** The states tab is the design board's sixth tab, a harness for the board comparison: never in a production build. */
const BOARD_STATES = process.env.NODE_ENV !== "production";

/** The board's sixth tab: the words every list shows when it is empty, read-only or failed. */
const EMPTY_STATES: { title: string; body: string }[] = [
  { title: "No exams yet", body: "Create an exam, attach a marking scheme version, then publish it to run sittings against it." },
  { title: "No draft exams", body: "Everything here is published. Clear the filter to see the whole catalogue." },
  { title: "No stations yet", body: "Create one with New station, from a template or straight from a prompt." },
  { title: "No matching stations", body: "Try a different name, or clear the exam filter." },
  { title: "No marking schemes", body: "Create a marking scheme, publish a version, then build exams and templates on it." },
  { title: "No saved templates yet", body: "The layouts on New template are starting points only. They are not added here until you finish the wizard (Save draft), then Publish from this list." },
  { title: "No programmes yet", body: "Add a programme for each exam you run sittings against." },
];

function StatesPanel() {
  return (
    <div id={`authoring-panel-${STATES_ID}`} role="tabpanel" className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {EMPTY_STATES.map((state) => (
        <div key={state.title} className={boardStateCard}>
          <h2 className="m-0 text-assess-desc font-semibold !leading-[normal] text-ink">{state.title}</h2>
          <p className={`m-0 ${boardMeta}`}>{state.body}</p>
        </div>
      ))}
      <div className={boardStateCard}>
        <div className={boardMeta}>Supervisor (no authoring rights)</div>
        <div>Lists show with no create or write buttons. Empty lists read &ldquo;Nothing here yet.&rdquo;</div>
      </div>
      <div className={boardStateCard}>
        <div className={ALERT}>
          Could not load more rubrics: network error
          <button type="button" className={boardButtonSmall}>Dismiss</button>
        </div>
        <div className={ALERT}>
          Could not load stations. <button type="button" className="p-0 text-osce-accent">Retry</button>
        </div>
      </div>
    </div>
  );
}

export function AuthoringHome({ section: sectionSlug }: { section?: string }) {
  const scope = useAuthoringScope();
  const { surface, hrefFor } = useSurface();
  const router = useRouter();
  // The staff console keeps its own page name; every organisation arm reads "Exams".
  const title = surface === "platform" ? "Authoring" : "Exams";
  const lead =
    surface === "platform"
      ? "Marking schemes, exams, programmes, templates and stations."
      : "Everything you examine with: the exams themselves, their stations, how they are marked, the layout a station follows, and which exams are offered for scheduling.";

  const items = useMemo(
    () => authoringTabItems(supportsProgrammes(scope)),
    [scope],
  );

  const showStates = BOARD_STATES && surface !== "platform" && sectionSlug === STATES_ID;
  const parsed = parseAuthoringSection(sectionSlug);
  const active =
    parsed && items.some((item) => item.id === parsed) ? parsed : DEFAULT_AUTHORING_SECTION;

  useEffect(() => {
    if (!sectionSlug) {
      router.replace(`${hrefFor("/authoring")}/${DEFAULT_AUTHORING_SECTION}`);
      return;
    }
    if (!parsed && !showStates) {
      router.replace(`${hrefFor("/authoring")}/${DEFAULT_AUTHORING_SECTION}`);
    }
  }, [sectionSlug, parsed, showStates, router, hrefFor]);

  const onTabChange = (id: string) => {
    router.push(`${hrefFor("/authoring")}/${id}`);
  };

  const panel = (
    <div id={`authoring-panel-${active}`} role="tabpanel" className={boardStack}>
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
        title={title}
        description={lead}
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
    <div className={cn(t.assessPage)} data-testid="exams-page">
      {/* pb-4: the board's empty actions box wraps under the title and adds a 16px row gap. */}
      <div className="pb-4">
        <div className={t.assessEyebrow}>Organise</div>
        <h1 className={t.assessTitle}>{title}</h1>
        <p className={cn(t.assessDesc, "m-0")}>{lead}</p>
      </div>
      <div
        className={boardTabs}
        role="tablist"
        aria-label="Authoring section"
      >
        {(BOARD_STATES ? [...items, { id: STATES_ID, label: STATES_LABEL }] : items).map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={showStates ? item.id === STATES_ID : active === item.id}
            onClick={() => onTabChange(item.id)}
            className={boardTab(showStates ? item.id === STATES_ID : active === item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {showStates ? <StatesPanel /> : panel}
    </div>
  );
}
