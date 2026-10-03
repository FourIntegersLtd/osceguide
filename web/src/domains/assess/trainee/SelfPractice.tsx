"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { HiOutlineSparkles } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CGroupedRow,
  B2CGroupedSection,
  B2CPageHeader,
  ButtonLink,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listOrgStations, type OrgStation } from "@/domains/assess/trainee/api";
import { practisable } from "@/domains/assess/trainee/support";

/**
 * An organisation's own stations, sat alone — list only; the four-step runner
 * lives on `practiceStation` like consumer library practise.
 */
export function SelfPractice({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => listOrgStations(orgSlug, signal), [orgSlug]);

  return (
    <div className="flex w-full min-w-0 flex-col gap-6">
      <B2CPageHeader
        className="!mb-0"
        eyebrow="Self practice"
        title="Your organisation's stations"
        subtitle="Sit one on your own, with the simulated patient and no supervisor. Nothing here is marked as an examination."
        action={
          <ButtonLink themeType="b2b" variant="secondary" size="sm" href={hrefFor("/stations")}>
            Platform library
          </ButtonLink>
        }
      />

      <AsyncBoundary
        state={state}
        isEmpty={(stations) => practisable(stations).length === 0}
        empty={{
          title: "No published stations yet",
          description:
            "Your organisation has not added any stations yet. Until it does, you can still practise with the OSCE Guide library.",
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
  const rows = useMemo(() => practisable(stations), [stations]);
  const withheld = stations.length - rows.length;

  return (
    <div className="flex flex-col gap-3">
      <B2CGroupedSection
        eyebrow={`${rows.length} station${rows.length === 1 ? "" : "s"} you can sit`}
      >
        {rows.map((station) => (
          <B2CGroupedRow
            key={station.id}
            icon={HiOutlineSparkles}
            title={station.title}
            meta={`${station.exam_code.toUpperCase()} · version ${station.version}`}
            onClick={() =>
              router.push(hrefFor(`/stations/${station.id}/practise?action=attempt`))
            }
          />
        ))}
      </B2CGroupedSection>
      {withheld > 0 ? (
        <p className="px-1 text-osce-meta text-b2b-mid">
          {withheld} more {withheld === 1 ? "is a draft" : "are drafts"} and cannot be sat until
          published.
        </p>
      ) : null}
    </div>
  );
}
