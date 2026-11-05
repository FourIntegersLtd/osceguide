import type { RailStep } from "@/foundation/ui";

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
      label: "Share the circuit's feedback",
      state: published ? "done" : "todo",
      note: published ? "Published" : "Not published yet",
    },
    { id: "results", label: "Results", state: "todo", note: "Admin decides and releases" },
  ];
  const line =
    left > 0
      ? `Mark the ${left === 1 ? "station" : `${left} stations`} left, then share one summary with the candidate.`
      : published
        ? "Everything is marked and shared. The admin decides and releases the result."
        : "Every station is marked. Share one summary with the candidate.";
  return { steps, line };
}

/** Unmarked stations first, then the rest in order: what is left leads. */
export function stationsToMark(stations: ReviewStation[]): ReviewStation[] {
  const sat = stations.filter((s) => s.state !== "not_sat");
  return [...sat.filter((s) => s.state === "unmarked"), ...sat.filter((s) => s.state === "marked")];
}
