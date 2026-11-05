"use client";

import { LuClipboardCheck } from "react-icons/lu";
import { B2CGroupedRowLink, B2CGroupedSection } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readSupervisorCircuits } from "@/domains/assess/dashboard/api";
import { readConsole } from "@/domains/assess/sessions/api";
import { slotReviewPath, unmarkedStations, type UnmarkedStation } from "@/domains/assess/sessions/support";

/** Ended circuits to look through: the newest few, so one home screen never reads the whole history. */
const CIRCUITS_LOOKED_AT = 10;

export type StationToReview = UnmarkedStation & {
  circuitName: string;
  sittingName: string;
  title: string;
};

/**
 * The stations a supervisor sat and has not marked yet, from reads that exist: the circuits they
 * are named on, then each ended circuit's console. The results index uses the hook; the
 * `StationsToReview` component below has no caller until the supervisor's Home mounts it. A failed read is an empty list: this is a prompt,
 * and the console it points at reports its own errors.
 */
export function useStationsToReview(orgSlug: string): { stations: StationToReview[] } {
  const state = useAsync(
    async (signal) => {
      const { items } = await readSupervisorCircuits(orgSlug, signal);
      const ended = (items ?? []).filter((row) => row.ended).slice(0, CIRCUITS_LOOKED_AT);
      // One circuit's failed read must not hide the others' stations.
      const consoles = await Promise.allSettled(
        ended.map(async (row) => ({ row, console: await readConsole(orgSlug, row.circuit_id, signal) })),
      );
      return consoles.flatMap((result) =>
        result.status === "fulfilled"
          ? unmarkedStations(result.value.console).map(({ slotId, attemptId, title }) => ({
              slotId,
              attemptId,
              title,
              circuitName: result.value.row.circuit_name,
              sittingName: result.value.row.sitting_name,
            }))
          : [],
      );
    },
    [orgSlug],
  );
  return { stations: state.error ? [] : (state.data ?? []) };
}

/** "Stations to review": one row per unmarked station. Renders nothing when there are none. */
export function StationsToReview({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const { stations } = useStationsToReview(orgSlug);
  if (stations.length === 0) return null;
  return (
    <B2CGroupedSection eyebrow="Stations to review">
      {stations.map((station) => (
        <B2CGroupedRowLink
          key={station.slotId}
          href={hrefFor(slotReviewPath(station))}
          icon={LuClipboardCheck}
          title={station.title}
          meta={`${station.sittingName} · ${station.circuitName}`}
        />
      ))}
    </B2CGroupedSection>
  );
}
