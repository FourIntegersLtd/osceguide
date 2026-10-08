/**
 * Where one candidate's result stands: marked, reviewed, decided, signed off,
 * released. Signing off while reviews are incomplete is allowed (decision R-2),
 * so the Reviewed step then says so instead of blocking.
 */

import type { RailStep } from "@/foundation/ui";
import { countNote, outcomeLabel } from "@/domains/assess/results/support";

export type CandidateStepId = "marked" | "reviewed" | "decided" | "signed_off" | "released";

export type CandidateProgressStep = RailStep<CandidateStepId>;

export interface ProgressCandidate {
  // `absent` (R-42) is declared here until the generated types are regenerated.
  stations?: { marked: boolean; absent?: boolean; overall_rag: unknown }[];
  decision: {
    assessment_outcome: string | null;
    signed_off_at: string | null;
    released_at: string | null;
  } | null;
}

/** The stations a candidate is owed marking and review for: an absent one (skipped, never sat) is not. */
export function owedMarking<T extends { absent?: boolean }>(stations: readonly T[]): T[] {
  return stations.filter((station) => !station.absent);
}

export function candidateProgress(candidate: ProgressCandidate): CandidateProgressStep[] {
  // A skipped station nobody marked is an absent result: it is not owed marking or review.
  const stations = owedMarking(candidate.stations ?? []);
  const decision = candidate.decision;
  const total = stations.length;
  const marked = stations.filter((station) => station.marked).length;
  const reviewed = stations.filter((station) => station.overall_rag !== null && station.overall_rag !== undefined).length;
  const reviewsDone = total > 0 && reviewed >= total;
  const signedOff = Boolean(decision?.signed_off_at);

  const reviewedStep: CandidateProgressStep = reviewsDone
    ? { id: "reviewed", label: "Reviewed", state: "done", note: countNote(reviewed, total, "reviewed") }
    : signedOff
      ? { id: "reviewed", label: "Reviewed", state: "attention", note: "Reviews not complete" }
      : { id: "reviewed", label: "Reviewed", state: "todo", note: countNote(reviewed, total, "reviewed") };

  return [
    {
      id: "marked",
      label: "Marked",
      state: total > 0 && marked >= total ? "done" : "todo",
      note: countNote(marked, total, "marked"),
    },
    reviewedStep,
    {
      id: "decided",
      label: "Decided",
      state: decision?.assessment_outcome ? "done" : "todo",
      note: decision?.assessment_outcome ? outcomeLabel(decision.assessment_outcome) : "Not decided",
    },
    { id: "signed_off", label: "Signed off", state: signedOff ? "done" : "todo", note: signedOff ? "Signed off" : "Not signed off" },
    {
      id: "released",
      label: "Released",
      state: decision?.released_at ? "done" : "todo",
      note: decision?.released_at ? "With the candidate" : "Not released",
    },
  ];
}

/** The word for the table's Status column: the furthest step reached. */
export function candidateStage(candidate: ProgressCandidate): string {
  const reached = candidateProgress(candidate).filter((step) => step.state === "done");
  return reached.at(-1)?.label ?? "Not marked";
}
