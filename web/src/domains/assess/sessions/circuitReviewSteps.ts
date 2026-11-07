import type { RailStep } from "@/foundation/ui";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import { markable, orderedSlots, stationLabel } from "@/domains/assess/sessions/support";

/** A station of an ended circuit, as the review step lists it. */
export type ReviewStation = {
  slotId: string;
  attemptId: string | null;
  position: number;
  title: string;
  /** "unmarked" is the supervisor's work; "not_sat" is a station nobody has started. */
  state: "unmarked" | "marked" | "not_sat";
};

export type CircuitReviewStepId = "mark" | "share" | "results";

/**
 * The three things left once a circuit ends: mark each station, share the circuit's feedback, and
 * the admin's decision. `published` is whether the circuit's feedback has been shared.
 */
export function circuitReviewSteps(
  stations: ReviewStation[],
  published: boolean,
): { steps: RailStep<CircuitReviewStepId>[]; line: string } {
  const sat = stations.filter((s) => s.state !== "not_sat");
  const marked = sat.filter((s) => s.state === "marked").length;
  const left = sat.length - marked;
  const steps: RailStep<CircuitReviewStepId>[] = [
    {
      id: "mark",
      label: "Mark each station",
      state: left === 0 ? "done" : "todo",
      note: `${marked} of ${sat.length} marked`,
    },
    {
      id: "share",
      label: "Send feedback",
      state: published ? "done" : "todo",
      note: published ? "Sent" : "Not sent yet",
    },
    { id: "results", label: "Results", state: "todo", note: "An admin shares the results" },
  ];
  const line =
    sat.length === 0
      ? "No one took part in this circuit, so there is nothing to mark."
      : left > 0
      ? `Mark ${left === 1 ? "the last station" : `the ${left} stations left`}. Then send feedback.`
      : published
        ? "Everything is marked and sent. An admin shares the results."
        : "Every station is marked. Now send feedback.";
  return { steps, line };
}

/** Unmarked stations first, then the rest in order: what is left leads. */
export function stationsToMark(stations: ReviewStation[]): ReviewStation[] {
  const sat = stations.filter((s) => s.state !== "not_sat");
  return [...sat.filter((s) => s.state === "unmarked"), ...sat.filter((s) => s.state === "marked")];
}

export type ReviewAction =
  | { kind: "mark"; label: string; station: ReviewStation }
  | { kind: "publish"; label: string }
  | { kind: "results"; label: string };

/** The one thing the ended hero offers: mark what is left, then share, then the results. */
export function nextReviewAction(stations: ReviewStation[], published: boolean): ReviewAction {
  const station = stationsToMark(stations).find((s) => s.state === "unmarked");
  if (station) return { kind: "mark", label: "Mark next station", station };
  const sat = stations.some((s) => s.state !== "not_sat");
  if (sat && !published) return { kind: "publish", label: "Send feedback" };
  return { kind: "results", label: "Open results" };
}

/** Each slot of the circuit as the review sees it. */
export function reviewStations(data: CircuitConsole): ReviewStation[] {
  return orderedSlots(data).map((slot) => ({
    slotId: slot.id,
    attemptId: slot.attempt_id ?? null,
    position: slot.slot_index + 1,
    title: stationLabel(slot),
    state: slot.marked ? "marked" : markable(slot) ? "unmarked" : "not_sat",
  }));
}
