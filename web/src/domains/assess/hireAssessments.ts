/** The Assessments list in a hire workspace: pills, the Next step chip and the no-exam state. Pure, so the words are tested. */
import type { BoardChipTone } from "@/foundation/ui/boardKit";
import type { AssessWords } from "@/capabilities/assess-words/vocabulary";
import { undecided } from "@/domains/assess/results/support";

export interface NextStepSitting {
  id: string;
  status: string;
  mode: string;
  scheduled_for: string | null;
  circuit_count: number;
  circuits?: { supervisor_user_id?: string | null }[];
}

/** One sitting's row of the results index; absent while it loads or when the person cannot read it. */
export interface DecisionRow {
  sat: number;
  not_decided: number;
  draft: number;
  signed_off: number;
  released: number;
}

export type AssessmentBucket = "upcoming" | "waiting" | "past";

const decideCount = (row: DecisionRow | undefined) => (row ? undecided(row) + row.draft : 0);
const releaseCount = (row: DecisionRow | undefined) => (row ? Math.max(row.signed_off, 0) : 0);

/** The one thing to do next, as a chip: Running, Add assessors, Decide N, Release N, Released. */
export function sittingNextStep(
  sitting: NextStepSitting,
  w: AssessWords,
  row: DecisionRow | undefined,
): { label: string; tone: BoardChipTone } {
  if (sitting.status === "cancelled") return { label: "Cancelled", tone: "neutral" };
  if (sitting.status === "in_progress" || sitting.status === "live") return { label: "Running", tone: "live" };
  if (sitting.status === "completed") {
    if (sitting.mode !== "exam") return { label: "Released", tone: "ok" };
    const decide = decideCount(row);
    if (decide > 0) return { label: `Decide ${decide}`, tone: "info" };
    if (!row) return { label: "Decide", tone: "info" };
    const release = releaseCount(row);
    if (release > 0) return { label: `Release ${release}`, tone: "info" };
    return { label: "Released", tone: "ok" };
  }
  if (sitting.circuit_count === 0) return { label: `Add ${w.circuits}`, tone: "warn" };
  if ((sitting.circuits ?? []).some((circuit) => !circuit.supervisor_user_id)) return { label: `Add ${w.supervisors}`, tone: "warn" };
  if (!sitting.scheduled_for) return { label: "Set a date", tone: "warn" };
  return { label: "Scheduled", tone: "info" };
}

const awaitingDecision = (sitting: NextStepSitting, row: DecisionRow | undefined) =>
  sitting.status === "completed" && sitting.mode === "exam" && (!row || decideCount(row) + releaseCount(row) > 0);

/** Upcoming is scheduled or running; waiting is a finished exam with a decision or release to make; past is the rest. */
export function assessmentBuckets<T extends NextStepSitting>(sittings: T[], index: Record<string, DecisionRow>) {
  const out: Record<AssessmentBucket, T[]> = { upcoming: [], waiting: [], past: [] };
  for (const sitting of sittings) {
    if (sitting.status === "scheduled" || sitting.status === "in_progress" || sitting.status === "live") {
      out.upcoming.push(sitting);
    } else if (awaitingDecision(sitting, index[sitting.id])) {
      out.waiting.push(sitting);
    } else {
      out.past.push(sitting);
    }
  }
  return out;
}

const PILL_WORDS: Record<AssessmentBucket, string> = { upcoming: "Upcoming", waiting: "Waiting for decisions", past: "Past" };

export function bucketLabel(bucket: AssessmentBucket, buckets: Record<AssessmentBucket, unknown[]>): string {
  return `${PILL_WORDS[bucket]} ${buckets[bucket].length}`;
}

/** No exam to schedule: the board's state, with the disabled Schedule button's reason. */
export function assessmentNoExam(w: AssessWords) {
  return {
    title: "You need an exam first",
    body: `${w.hiring ? "An" : "A"} ${w.sitting} runs an exam. Start from one of ours or build your own.`,
    action: "Set up an exam",
    why: "Scheduling needs an exam available for scheduling.",
  };
}
