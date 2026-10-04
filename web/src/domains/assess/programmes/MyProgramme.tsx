"use client";

import { LuCircle, LuCircleCheck } from "react-icons/lu";
import { B2CGroupedRow, B2CGroupedSection, B2CPageHeader, Badge, BandPill, EmptyState, Panel } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { PreviewNotice } from "@/domains/assess/programmes/parts";
import { PREVIEW_MY_PROGRAMME, type MyProgrammeData } from "@/domains/assess/programmes/preview";

const STATE_LABEL: Record<MyProgrammeData["stages"][number]["state"], string> = {
  signed_off: "Signed off",
  current: "You are here",
  upcoming: "Not started",
};

/**
 * A programme, as the person in it sees it.
 *
 * Their stages, their modules and who can see their practice. Nothing tells
 * the browser which programmes a trainee is in (`/me/sittings` is the only
 * thing they can ask), so this reads the sample in `preview.ts` and My
 * training does not link here yet.
 */
export function MyProgramme({ programmeId }: { programmeId: string }) {
  const { hrefFor } = useSurface();
  const back = { href: hrefFor("/trainee"), label: "My training" };
  const programme = PREVIEW_MY_PROGRAMME.id === programmeId ? PREVIEW_MY_PROGRAMME : null;

  if (!programme) {
    return (
      <div className="flex flex-col gap-6">
        <B2CPageHeader back={back} title="Programme" />
        <EmptyState
          title="No such programme"
          description="This page shows sample data until the API can return your programmes."
        />
      </div>
    );
  }

  const done = programme.modules.filter((module) => module.done).length;
  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader back={back} title={programme.name} subtitle={programme.summary} />
      <PreviewNotice needs="No route returns the programmes a trainee is in." />

      <ol className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {programme.stages.map((stage, index) => (
          <li key={stage.title} className="rounded-panel border border-b2b-border bg-b2b-surface p-5">
            <p className="text-osce-caption font-medium text-b2b-mid">Stage {index + 1}</p>
            <p className="mt-2 text-osce-body font-semibold text-b2b-headline">{stage.title}</p>
            <p className="mt-1 text-osce-meta text-b2b-mid">{stage.detail}</p>
            <div className="mt-3">
              <Badge variant={stage.state === "signed_off" ? "success" : "neutral"} dot>
                {STATE_LABEL[stage.state]}
              </Badge>
            </div>
          </li>
        ))}
      </ol>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <B2CGroupedSection eyebrow={`Modules · ${done} of ${programme.modules.length} done`}>
          {programme.modules.map((module) => (
            <B2CGroupedRow
              key={module.title}
              icon={module.done ? LuCircleCheck : LuCircle}
              title={module.title}
              meta={module.meta}
              trailing={module.band ? <BandPill variant={module.band} /> : undefined}
            />
          ))}
        </B2CGroupedSection>

        <Panel title="Your supervisor" className="self-start">
          <p className="text-osce-body font-medium text-b2b-headline">{programme.supervisor.name}</p>
          <p className="text-osce-meta text-b2b-mid">{programme.supervisor.role}</p>
          <p className="mt-3 text-osce-meta text-b2b-mid">{programme.supervisor.visibility}</p>
        </Panel>
      </div>
    </div>
  );
}
