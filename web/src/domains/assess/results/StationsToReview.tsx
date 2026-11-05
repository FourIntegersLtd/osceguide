"use client";

import { LuClipboardCheck } from "react-icons/lu";
import { B2CGroupedRowLink, B2CGroupedSection, Badge } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readSupervisorCircuits } from "@/domains/assess/dashboard/api";
import { stillToReviewLine } from "@/domains/assess/dashboard/support";
import { readCircuitReview, readConsole } from "@/domains/assess/sessions/api";
import { markable, orderedSlots, slotReviewPath, unmarkedStations, type UnmarkedStation } from "@/domains/assess/sessions/support";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/** Ended circuits to look through: the newest few, so one home screen never reads the whole history. */
const CIRCUITS_LOOKED_AT = 10;

export type StationToReview = UnmarkedStation & {
  circuitName: string;
  sittingName: string;
  title: string;
};

/** One ended circuit: how many candidates are still to review, or that its feedback is ready to publish. */
export type CircuitToReview = {
  circuitId: string;
  circuitName: string;
  sittingName: string;
  /** Candidates who sat a markable station. */
  candidates: number;
  /** Of those, candidates with a station still unmarked. */
  toReview: number;
  stations: StationToReview[];
  /** Every sat station is marked and the circuit's feedback is not published yet. */
  readyToPublish: boolean;
};

/**
 * The stations a supervisor sat and has not marked yet, grouped by circuit, from reads that exist:
 * the circuits they are named on, each ended circuit's console, and whether its feedback is published.
 * A failed read is an empty list: this is a prompt, and the console it points at reports its own errors.
 */
export function useStationsToReview(orgSlug: string | null): { stations: StationToReview[]; circuits: CircuitToReview[] } {
  const state = useAsync(
    async (signal) => {
      if (!orgSlug) return [];
      const { items } = await readSupervisorCircuits(orgSlug, signal);
      const ended = (items ?? []).filter((row) => row.ended).slice(0, CIRCUITS_LOOKED_AT);
      // One circuit's failed read must not hide the others' stations.
      const settled = await Promise.allSettled(
        ended.map(async (row) => {
          const console = await readConsole(orgSlug, row.circuit_id, signal);
          const stations: StationToReview[] = unmarkedStations(console).map(({ slotId, attemptId, title }) => ({
            slotId,
            attemptId,
            title,
            circuitName: row.circuit_name,
            sittingName: row.sitting_name,
          }));
          const sat = orderedSlots(console).filter((slot) => markable(slot));
          const candidates = new Set(sat.map((slot) => slot.trainee.user_id)).size;
          const toReview = new Set(sat.filter((slot) => !slot.has_review).map((slot) => slot.trainee.user_id)).size;
          const published =
            stations.length === 0 && sat.length > 0
              ? // A prompt: a failed read only means no "Ready to publish" row; the circuit page reports its own errors.
                // eslint-disable-next-line no-restricted-syntax
                (await readCircuitReview(orgSlug, row.circuit_id, signal).catch(() => null))?.state === "published"
              : true;
          return {
            circuitId: row.circuit_id,
            circuitName: row.circuit_name,
            sittingName: row.sitting_name,
            candidates,
            toReview,
            stations,
            readyToPublish: stations.length === 0 && sat.length > 0 && !published,
          } satisfies CircuitToReview;
        }),
      );
      return settled.flatMap((result) => (result.status === "fulfilled" ? [result.value] : []));
    },
    [orgSlug],
  );
  const circuits = state.error ? [] : (state.data ?? []);
  return { circuits, stations: circuits.flatMap((circuit) => circuit.stations) };
}

/** "Stations to review", grouped by circuit. Renders nothing when there is nothing to review or publish. */
export function StationsToReview({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const w = useAssessWords();
  const { circuits } = useStationsToReview(orgSlug);
  const rows = circuits.filter((circuit) => circuit.stations.length > 0 || circuit.readyToPublish);
  if (rows.length === 0) return null;
  return (
    <B2CGroupedSection eyebrow="Stations to review" action={<span className="text-osce-meta text-b2b-muted">Grouped by circuit</span>}>
      {rows.map((circuit) => {
        const first = circuit.stations[0];
        return (
          <B2CGroupedRowLink
            key={circuit.circuitId}
            href={hrefFor(first ? slotReviewPath(first) : `/circuits/${circuit.circuitId}`)}
            icon={LuClipboardCheck}
            title={`${circuit.sittingName} · ${circuit.circuitName}`}
            meta={
              first
                ? stillToReviewLine(circuit.toReview, circuit.candidates, w)
                : "Every review done. Publish circuit feedback to finalise and let trainees read it."
            }
            trailing={
              first ? (
                <Badge variant="warning" dot>{`${circuit.stations.length} to review`}</Badge>
              ) : (
                <Badge variant="success" dot>Ready to publish</Badge>
              )
            }
          />
        );
      })}
    </B2CGroupedSection>
  );
}
