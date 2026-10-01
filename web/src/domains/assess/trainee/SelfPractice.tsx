"use client";

import { useMemo } from "react";
import { useRouter } from "next/navigation";
import { HiChevronRight, HiOutlineSparkles } from "react-icons/hi2";
import { AsyncBoundary, ButtonLink, b2bTokens } from "@/foundation/ui";
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
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-b2b-border pb-4">
        <div className="min-w-0">
          <p className={b2bTokens.b2bEyebrow}>Self practice</p>
          <h1 className={`mt-1 ${b2bTokens.b2bPageTitle}`}>Your organisation&apos;s stations</h1>
          <p className={`mt-1 ${b2bTokens.b2bHeroSubtitle} ${b2bTokens.b2bProseMeasure}`}>
            Sit one on your own, with the simulated patient and no supervisor. Nothing here is
            marked as an examination.
          </p>
        </div>
        <ButtonLink themeType="b2b" variant="secondary" size="sm" href={hrefFor("/stations")}>
          Platform library
        </ButtonLink>
      </header>

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
    <section className="space-y-2">
      <p className={b2bTokens.b2bEyebrow}>
        {rows.length} station{rows.length === 1 ? "" : "s"} you can sit
      </p>
      <div className={b2bTokens.b2bGroupedShell}>
        {rows.map((station) => (
          <button
            key={station.id}
            type="button"
            onClick={() =>
              router.push(hrefFor(`/stations/${station.id}/practise?action=attempt`))
            }
            className={`${b2bTokens.b2bGroupedRow} w-full text-left`}
          >
            <span className={`${b2bTokens.b2bIconChipBase} ${b2bTokens.b2bChipHueClasses.amber}`}>
              <HiOutlineSparkles className="h-5 w-5" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className={b2bTokens.b2bGroupedRowTitle}>{station.title}</p>
              <p className={b2bTokens.b2bGroupedRowSubtitle}>
                {station.exam_code.toUpperCase()} · version {station.version}
              </p>
            </div>
            <HiChevronRight className="h-5 w-5 shrink-0 text-b2b-inactive" aria-hidden />
          </button>
        ))}
      </div>
      {withheld > 0 ? (
        <p className="text-osce-caption text-b2b-mid">
          {withheld} more {withheld === 1 ? "is a draft" : "are drafts"} and cannot be sat until
          published.
        </p>
      ) : null}
    </section>
  );
}
