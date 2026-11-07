/**
 * The Sittings list's job-shaped views, the "Next step" on a row, the Results
 * index's "Where it is" and the empty-state choice. Pure, so the words are tested.
 * Everything is derived from fields the two lists already carry.
 */

import { plural } from "@/foundation/format";
import type { AssessWords } from "@/domains/assess/vocabulary";
import { sittingNext } from "@/domains/assess/sittingSteps";
import { undecided } from "@/domains/assess/results/support";

export interface ListSitting {
  id: string;
  mode: string;
  status: string;
  scheduled_for?: string | null;
  circuit_count: number;
  /** The list may omit them; `circuit_count` then says how many there are. */
  circuits?: { started_at: string | null; ended_at: string | null }[];
}

export interface ListResultsRow {
  mode: string;
  candidates: number;
  sat?: number;
  not_decided: number;
  draft: number;
  signed_off: number;
  released?: number;
}

export type SittingPreset = "" | "upcoming" | "decisions" | "past";

/** "Waiting for decisions" is an exam-mode view; the other two read the status. */
export function matchesPreset(
  sitting: ListSitting,
  preset: SittingPreset,
  waitingIds: ReadonlySet<string>,
): boolean {
  switch (preset) {
    case "upcoming":
      return sitting.status === "scheduled" || sitting.status === "in_progress";
    case "decisions":
      return sitting.mode === "exam" && waitingIds.has(sitting.id);
    case "past":
      return sitting.status === "completed" || sitting.status === "cancelled";
    default:
      return true;
  }
}

/** Ids of exam sittings whose results still wait on a decision or a sign-off. */
export function waitingForDecisions(rows: (ListResultsRow & { sitting_id: string })[]): Set<string> {
  return new Set(
    rows
      .filter((row) => row.mode === "exam" && (undecided(row) > 0 || row.draft > 0 || row.signed_off > (row.released ?? 0)))
      .map((row) => row.sitting_id),
  );
}

/** What to do next with this sitting, in one or two words. */
export function sittingNextStep(
  sitting: ListSitting,
  results: ListResultsRow | undefined,
  can: { schedule: boolean; signOff: boolean },
  words: AssessWords,
): string {
  if (sitting.status === "cancelled") return "None";
  const training = sitting.mode !== "exam";
  if (sitting.status !== "completed") {
    const next = sittingNext({
      scheduledFor: sitting.scheduled_for ?? null,
      circuits: sitting.circuits?.length
        ? sitting.circuits
        : Array.from({ length: sitting.circuit_count }, () => ({ started_at: null, ended_at: null })),
      counts: null,
      training,
      can,
    });
    if (next.id === "schedule") return "Set a date";
    if (next.id === "circuits") return words.hiring ? `Add ${words.supervisors}` : "Add circuits";
    return sitting.status === "in_progress" ? "Running" : "Run it";
  }
  if (training) return "Share feedback";
  if (!results) return "Open results";
  const left = undecided(results) + results.draft;
  if (left > 0) return can.signOff ? `Decide ${left}` : `${left} to decide`;
  if (results.signed_off > (results.released ?? 0)) return can.signOff ? "Release" : "Waiting to release";
  if ((results.released ?? 0) > 0) return "Released";
  return "Open results";
}

/** The Results index's "Where it is", from the counts the row already has. */
export function resultsWhere(row: ListResultsRow): string {
  if (row.mode !== "exam") return "Feedback only";
  if (row.sat === 0) return "Nobody has sat yet";
  const left = undecided(row) + row.draft;
  if (left > 0) return `${plural(left, "decision")} to make`;
  if (row.signed_off > 0) return "Signed off, not released";
  if ((row.released ?? 0) > 0) return "Released";
  return "Nothing to decide yet";
}

/** One line on what the two kinds of sitting do; null when it would explain nothing. */
export function modeNote(sittings: { mode: string }[], canSchedule: boolean, w: AssessWords): string | null {
  const both = sittings.some((s) => s.mode === "exam") && sittings.some((s) => s.mode !== "exam");
  if (!both && !canSchedule) return null;
  return `Training ${w.sittings} give feedback only. ${w.hiring ? "Hiring decisions" : "Decisions"} are made on Exam ${w.sittings}.`;
}

/** With no active exam there is nothing to schedule, so the empty state sends the viewer to build one. */
export function needsExamFirst(programmes: { status: string }[]): boolean {
  return !programmes.some((programme) => programme.status === "active");
}
