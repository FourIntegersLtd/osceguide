"use client";

import { LuClipboardCheck } from "react-icons/lu";
import { B2CGroupedRowLink, B2CGroupedSection } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readSupervisorCircuits } from "@/domains/assess/dashboard/api";
import { readConsole } from "@/domains/assess/sessions/api";
import { markable } from "@/domains/assess/sessions/support";
import { slotReviewPath, type UnmarkedStation } from "@/domains/assess/results/support";

/** Ended circuits to look through: the newest few, so one home screen never reads the whole history. */
const CIRCUITS_LOOKED_AT = 10;

export type StationToReview = UnmarkedStation & {
  circuitName: string;
  sittingName: string;
  title: string;
};

/**
 * The stations a supervisor sat and has not marked yet, from reads that exist: the circuits they
 * are named on, then each ended circuit's console. Mounted by the results index and, as
 * `StationsToReview`, by the supervisor's Home. A failed read is an empty list: this is a prompt,
 * and the console it points at reports its own errors.
 */
export function useStationsToReview(orgSlug: string): { stations: StationToReview[]; loading: boolean } {
  const state = useAsync(
    async (signal) => {
      const { items } = await readSupervisorCircuits(orgSlug, signal);
      const ended = (items ?? []).filter((row) => row.ended).slice(-CIRCUITS_LOOKED_AT);
      const consoles = await Promise.all(
        ended.map(async (row) => ({ row, console: await readConsole(orgSlug, row.circuit_id, signal) })),
      );
      return consoles.flatMap(({ row, console }) =>
        (console.slots ?? [])
          .filter((slot) => !slot.has_review && markable(slot))
          .map((slot) => ({
            slotId: slot.id,
            attemptId: slot.attempt_id ?? null,
            circuitName: row.circuit_name,
            sittingName: row.sitting_name,
            title: slot.station?.title ?? "Station",
          })),
      );
    },
    [orgSlug],
  );
  return { stations: state.error ? [] : (state.data ?? []), loading: state.loading };
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
