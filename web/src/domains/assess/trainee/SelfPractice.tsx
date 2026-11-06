"use client";

import { useMemo, useState } from "react";
import { AsyncBoundary, ButtonLink, SectionSearchField } from "@/foundation/ui";
import { boardChip } from "@/foundation/ui/boardKit";
import {
  TraineeHead,
  TraineeList,
  TraineePage,
  TraineeRow,
} from "@/domains/assess/trainee/traineeBoard";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  stationAttemptPath,
  stationFeedbackPath,
} from "@/capabilities/station-runner/stationPaths";
import { listOrgStations, type OrgStation } from "@/domains/assess/trainee/api";
import { practisable } from "@/domains/assess/trainee/support";

/**
 * An organisation's own stations, sat alone — list only; the four-step runner
 * lives on `practiceStation` like consumer library practise.
 */
export function SelfPractice({ orgSlug }: { orgSlug: string }) {
  const state = useAsync(
    (signal) => listOrgStations(orgSlug, signal),
    [orgSlug],
  );

  return (
    <TraineePage label="Self practice">
      <TraineeHead
        eyebrow="Practise"
        title="Self practice"
        desc="Your organisation's stations. Nothing here is marked for the record."
      />

      <AsyncBoundary
        state={state}
        isEmpty={(stations) => practisable(stations).length === 0}
        empty={{
          title: "No published stations yet",
          description:
            "Your organisation has not added any stations yet. Ask your administrator when they will be ready.",
        }}
      >
        {(stations) => <StationList stations={stations} />}
      </AsyncBoundary>
    </TraineePage>
  );
}

function StationList({ stations }: { stations: readonly OrgStation[] }) {
  const { hrefFor } = useSurface();
  const [query, setQuery] = useState("");
  const all = useMemo(() => practisable(stations), [stations]);
  const needle = query.trim().toLowerCase();
  const rows = needle
    ? all.filter((station) => station.title.toLowerCase().includes(needle))
    : all;
  const withheld = stations.length - all.length;

  return (
    <>
      <div className="max-w-[420px]">
        <SectionSearchField
          value={query}
          onChange={setQuery}
          placeholder="Search stations"
        />
      </div>
      <TraineeList
        untitled
        title={`${rows.length} station${rows.length === 1 ? "" : "s"} you can sit`}
      >
        {rows.map((station) => (
          <TraineeRow
            key={station.id}
            title={station.title}
            meta={`${station.exam_code.toUpperCase()} · version ${station.version}`}
          >
            <span className={boardChip("neutral")}>
              {station.exam_code.toUpperCase()}
            </span>
            <ButtonLink
              themeType="b2b"
              variant="secondary"
              size="sm"
              href={hrefFor(stationAttemptPath(station.id))}
            >
              Practise
            </ButtonLink>
            <ButtonLink
              themeType="b2b"
              variant="ghost"
              size="sm"
              href={hrefFor(stationFeedbackPath(station.id))}
            >
              Past feedback
            </ButtonLink>
          </TraineeRow>
        ))}
      </TraineeList>
      {withheld > 0 ? (
        <p className="px-1 text-osce-meta text-b2b-mid">
          {withheld} more {withheld === 1 ? "is a draft" : "are drafts"} and
          cannot be sat until published.
        </p>
      ) : null}
    </>
  );
}
