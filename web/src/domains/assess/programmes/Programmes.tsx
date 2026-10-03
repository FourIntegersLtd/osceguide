"use client";

import { LuLayoutList } from "react-icons/lu";
import { B2CGroupedRowLink, B2CGroupedSection, B2CPageHeader, Badge, ButtonLink } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { PreviewNotice } from "@/domains/assess/programmes/parts";
import { PREVIEW_PROGRAMMES, type ProgrammeSummary } from "@/domains/assess/programmes/preview";
import { PURPOSES, purposeCopy } from "@/domains/assess/programmes/purposes";

function peopleLabel(programme: ProgrammeSummary): string {
  const [one, many] = purposeCopy(programme.purpose).person;
  return `${programme.people} ${programme.people === 1 ? one : many}`;
}

/**
 * Every programme the organisation runs, grouped by what it is for.
 *
 * `GET /orgs/{slug}/programmes` answers with an exam and a status only: no
 * purpose, no people count and no "where it is". Until it does, the rows are
 * the sample in `preview.ts`.
 */
export function Programmes() {
  const { hrefFor } = useSurface();
  const programmes = PREVIEW_PROGRAMMES;

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Programmes"
        subtitle="A programme has a purpose, the people in it and the stations they practise. Choose the purpose and the right defaults follow: who joins, how it is marked and what people get at the end."
        action={
          <ButtonLink href={hrefFor("/programmes/new")} themeType="b2b" variant="commit">
            New programme
          </ButtonLink>
        }
      />
      <PreviewNotice needs="The programmes route returns no purpose, people count or progress." />

      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {PURPOSES.map((purpose) => {
          const count = programmes.filter((programme) => programme.purpose === purpose.id).length;
          return (
            <li key={purpose.id} className="rounded-panel border border-b2b-border bg-b2b-surface p-5">
              <p className="text-osce-caption font-medium text-b2b-mid">
                {purpose.label} · {purpose.when}
              </p>
              <p className="mt-2 text-osce-body font-semibold text-b2b-headline">{purpose.headline}</p>
              <p className="mt-1 text-osce-meta text-b2b-mid">{purpose.stages.join(" → ")}</p>
              <p className="mt-3 text-osce-meta tabular-nums text-b2b-mid">
                {count} {count === 1 ? "programme" : "programmes"}
              </p>
            </li>
          );
        })}
      </ul>

      <B2CGroupedSection eyebrow="All programmes">
        {programmes.map((programme) => (
          <B2CGroupedRowLink
            key={programme.id}
            /* An exam programme is its sittings; the other four have a page of their own. */
            href={hrefFor(
              programme.purpose === "exam_preparation" ? "/sittings" : `/programmes/${programme.id}`,
            )}
            icon={LuLayoutList}
            title={programme.name}
            meta={[purposeCopy(programme.purpose).label, peopleLabel(programme), programme.whereItIs].join(" · ")}
            trailing={
              <Badge variant={programme.status === "Running" ? "success" : "neutral"} dot>
                {programme.status}
              </Badge>
            }
          />
        ))}
      </B2CGroupedSection>
    </div>
  );
}
