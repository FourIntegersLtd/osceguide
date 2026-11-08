"use client";

import { b2bTokens } from "@/foundation/ui";
import { boardChip } from "@/foundation/ui/boardKit";
import { BoardRow, BoardSection, RowChevron, RowText } from "@/domains/assess/dashboard/BoardParts";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readSupervisorCircuits } from "@/domains/assess/dashboard/api";
import { draftsWaitingLine, stillToReviewLine } from "@/domains/assess/dashboard/support";
import { readCircuitReview, readConsole } from "@/domains/assess/sessions/api";
import { slotReviewPath, summariseCircuit, type UnmarkedStation } from "@/domains/assess/sessions/support";
import { useAssessWords } from "@/capabilities/assess-words";

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
  /** Reviews started and not yet completed. */
  drafts: number;
  stations: StationToReview[];
  /** Every sat station is marked and the circuit's feedback is not published yet. */
  readyToPublish: boolean;
};

/**
 * The stations a supervisor sat and has not marked yet, grouped by circuit, from reads that exist:
 * the circuits they are named on, each ended circuit's console, and whether its feedback is published.
 * A failed read is an empty list, and a failed review read is "not ready": this is a prompt, and the console it points at reports its own errors.
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
          const summary = summariseCircuit(console, null);
          // Only a circuit with everything marked asks whether its feedback is published; a failed
          // read leaves it null, which is "not ready": unknown is never "Ready to publish".
          const review =
            summary.unmarked.length === 0 && summary.candidates > 0 ? await readReviewOrNull(orgSlug, row.circuit_id, signal) : null;
          const { unmarked, ...counts } = summariseCircuit(console, review);
          return {
            circuitId: row.circuit_id,
            circuitName: row.circuit_name,
            sittingName: row.sitting_name,
            ...counts,
            stations: unmarked.map(({ slotId, attemptId, title }) => ({
              slotId,
              attemptId,
              title,
              circuitName: row.circuit_name,
              sittingName: row.sitting_name,
            })),
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

async function readReviewOrNull(orgSlug: string, circuitId: string, signal: AbortSignal) {
  try {
    return await readCircuitReview(orgSlug, circuitId, signal);
  } catch {
    return null;
  }
}

/** "Stations to review" for a supervisor's own home: fetches, then draws the list. */
export function StationsToReview({ orgSlug }: { orgSlug: string }) {
  const { circuits } = useStationsToReview(orgSlug);
  return <StationsToReviewList circuits={circuits} />;
}

/** The circuits with work left, each a row with how much of it is reviewed. Renders nothing when there is nothing to review or publish. */
export function StationsToReviewList({ circuits }: { circuits: readonly CircuitToReview[] }) {
  const { hrefFor } = useSurface();
  const w = useAssessWords();
  const rows = circuits.filter((circuit) => circuit.stations.length > 0 || circuit.readyToPublish);
  if (rows.length === 0) return null;
  return (
    <BoardSection title="Stations to review" aside={<span className={b2bTokens.assessMeta}>Grouped by circuit</span>}>
      {rows.map((circuit, index) => {
        const first = circuit.stations[0];
        const done = first && circuit.candidates > 0 ? Math.round(((circuit.candidates - circuit.toReview) / circuit.candidates) * 100) : 100;
        const title = `${circuit.sittingName} · ${circuit.circuitName}`;
        return (
          <BoardRow key={circuit.circuitId} href={hrefFor(first ? slotReviewPath(first) : `/circuits/${circuit.circuitId}`)} first={index === 0}>
            <RowText
              title={title}
              meta={
                first
                  ? circuit.drafts > 0
                    ? draftsWaitingLine(circuit.drafts)
                    : stillToReviewLine(circuit.toReview, circuit.candidates, w)
                  : `Every review done. Send feedback so ${w.trainees} read it.`
              }
            />
            <div
              role="progressbar"
              aria-label={`${title} reviewed`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={done}
              className="h-2 w-[140px] shrink-0 overflow-hidden rounded-full bg-osce-navActive max-[900px]:w-full"
            >
              <div className="h-2 rounded-full bg-osce-accent" style={{ width: `${done}%` }} />
            </div>
            <span className={boardChip(first ? "warn" : "ok")}>
              {first ? (circuit.drafts > 0 ? `${circuit.drafts} ${circuit.drafts === 1 ? "draft" : "drafts"}` : `${circuit.stations.length} to review`) : "Ready to publish"}
            </span>
            <RowChevron />
          </BoardRow>
        );
      })}
    </BoardSection>
  );
}
