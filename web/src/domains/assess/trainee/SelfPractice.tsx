"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { HiOutlineSparkles } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CGroupedRow,
  B2CGroupedSection,
  B2CHero,
  B2CPageHeader,
  ButtonLink,
  SectionSearchField,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { stationAttemptPath, stationFeedbackPath } from "@/capabilities/station-runner/stationFeedbackPath";
import { listOrgStations, type OrgStation } from "@/domains/assess/trainee/api";
import { PERSONAL_PRACTICE_HREF, practisable } from "@/domains/assess/trainee/support";

/**
 * An organisation's own stations, sat alone — list only; the four-step runner
 * lives on `practiceStation` like consumer library practise.
 */
export function SelfPractice({ orgSlug }: { orgSlug: string }) {
  const state = useAsync((signal) => listOrgStations(orgSlug, signal), [orgSlug]);

  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <B2CPageHeader
        className="!mb-0"
        title="Self practice"
        subtitle="Your organisation's stations. Nothing here is marked for the record."
      />

      <AsyncBoundary
        state={state}
        isEmpty={(stations) => practisable(stations).length === 0}
        empty={{
          title: "No published stations yet",
          description:
            "Your organisation has not added any stations yet. Until it does, you can still practise with the OSCE Guide library.",
          action: (
            <ButtonLink themeType="b2b" variant="secondary" size="sm" href={PERSONAL_PRACTICE_HREF}>
              Open personal practice
            </ButtonLink>
          ),
        }}
      >
        {(stations) => <StationList stations={stations} />}
      </AsyncBoundary>
    </div>
  );
}

function StationList({ stations }: { stations: readonly OrgStation[] }) {
  const router = useRouter();
  const { hrefFor } = useSurface();
  const [query, setQuery] = useState("");
  const all = useMemo(() => practisable(stations), [stations]);
  const needle = query.trim().toLowerCase();
  const rows = needle ? all.filter((station) => station.title.toLowerCase().includes(needle)) : all;
  const withheld = stations.length - all.length;

  return (
    <div className="flex flex-col gap-3">
      <SectionSearchField value={query} onChange={setQuery} placeholder="Search stations" />
      <B2CGroupedSection
        eyebrow={`${rows.length} station${rows.length === 1 ? "" : "s"} you can sit`}
      >
        {rows.map((station) => (
          // Beside the row, not inside it: the row is a button that starts an attempt.
          <div key={station.id} className="flex items-center gap-2">
            <div className="min-w-0 flex-1">
              <B2CGroupedRow
                icon={HiOutlineSparkles}
                title={station.title}
                meta={`${station.exam_code.toUpperCase()} · version ${station.version}`}
                onClick={() =>
                  router.push(hrefFor(stationAttemptPath(station.id)))
                }
              />
            </div>
            <ButtonLink
              themeType="b2b"
              variant="ghost"
              size="sm"
              href={hrefFor(stationFeedbackPath(station.id))}
            >
              Past feedback
            </ButtonLink>
          </div>
        ))}
      </B2CGroupedSection>
      <B2CHero
        eyebrow="Want every station for your exam?"
        title="Your personal practice"
        action={
          <ButtonLink
            themeType="b2b"
            variant="secondary"
            size="sm"
            href={PERSONAL_PRACTICE_HREF}
          >
            Open personal practice
          </ButtonLink>
        }
      >
        The full OSCE Guide library for your exam, with debriefs only you see.
      </B2CHero>
      {withheld > 0 ? (
        <p className="px-1 text-osce-meta text-b2b-mid">
          {withheld} more {withheld === 1 ? "is a draft" : "are drafts"} and cannot be sat until
          published.
        </p>
      ) : null}
    </div>
  );
}
