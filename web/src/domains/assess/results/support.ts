import type { AssessWords } from "@/capabilities/assess-words";
import { sittingWhen } from "@/domains/assess/sittingWords";
import { slotReviewPath, type UnmarkedStation } from "@/domains/assess/sessions/support";
import type {
  CandidateReport,
  CohortCandidate,
  SittingReadout,
} from "@/domains/assess/results/api";

/**
 * The vocabulary and the arithmetic behind the results screens.
 *
 * Pure, so the things that decide what a candidate is told — which outcomes
 * exist, what a decision was judged against, whether it is safe to sign off —
 * can be tested rather than read off a component.
 */

/**
 * The four outcomes, as the backend's pattern spells them.
 *
 * The rebuilt screen offered "borderline", which `SaveDecision` rejects: the
 * unresolved outcomes here are `inconclusive` and `withheld`, and they mean
 * different things. Getting this list wrong is a 422 at the moment somebody is
 * trying to record a result.
 */
export const ASSESSMENT_OUTCOMES = ["pass", "fail", "inconclusive", "withheld"] as const;
export type AssessmentOutcome = (typeof ASSESSMENT_OUTCOMES)[number];

/** A stored outcome as a pick, or "" when none is chosen (or the server sent one this screen does not know). */
export function outcomeChoice(raw: string | null | undefined): AssessmentOutcome | "" {
  return ASSESSMENT_OUTCOMES.find((outcome) => outcome === raw) ?? "";
}

export const OUTCOME_LABEL: Record<AssessmentOutcome, string> = {
  pass: "Pass",
  fail: "Fail",
  inconclusive: "Inconclusive",
  withheld: "Withheld",
};

const OUTCOME_HINT: Record<AssessmentOutcome, string> = {
  pass: "Met the standard.",
  fail: "Did not meet the standard.",
  inconclusive: "Not enough was assessed to decide.",
  withheld: "Decided, but held back, for example during an appeal.",
};

/** The line under an outcome choice; an employer is told what too little means. */
export function outcomeHint(outcome: AssessmentOutcome, w: AssessWords): string {
  return w.hiring && outcome === "inconclusive" ? "This candidate sat too few stations for a pass or fail." : OUTCOME_HINT[outcome];
}

/** Whether the employer is taking the candidate on. Recorded only on an exam-mode sitting (hire). */
export const RECRUITMENT_OUTCOMES = ["pending", "hired", "reserve", "not_hired", "withdrawn"] as const;
/** The four hiring decisions a person can choose; "pending" is only what is stored before one is made. */
export const RECRUITMENT_PILLS = ["hired", "reserve", "not_hired", "withdrawn"] as const;

export type RecruitmentOutcome = (typeof RECRUITMENT_OUTCOMES)[number];

export const RECRUITMENT_LABEL: Record<RecruitmentOutcome, string> = {
  pending: "Pending",
  hired: "Hired",
  reserve: "Reserve list",
  not_hired: "Not hired",
  withdrawn: "Withdrawn",
};

/** The words for a stored recruitment outcome; an unknown value is shown as it came. */
export function recruitmentLabel(value: string): string {
  const known = RECRUITMENT_OUTCOMES.find((outcome) => outcome === value);
  return known ? RECRUITMENT_LABEL[known] : value;
}

export function outcomeLabel(outcome: string): string {
  return OUTCOME_LABEL[outcome as AssessmentOutcome] ?? outcome;
}

export function outcomeTone(
  outcome: string | null | undefined,
): "success" | "danger" | "warning" | "neutral" {
  if (outcome === "pass") return "success";
  if (outcome === "fail") return "danger";
  if (outcome === "inconclusive" || outcome === "withheld") return "warning";
  return "neutral";
}

/* ---------- where a decision has got to ---------- */

export const WORKFLOW_LABEL: Record<string, string> = {
  draft: "Draft",
  signed_off: "Signed off",
  released: "Released",
};

export function workflowLabel(state: string | null | undefined): string {
  if (!state) return "Not decided";
  return WORKFLOW_LABEL[state] ?? state.replace(/_/g, " ");
}

export function workflowTone(state: string | null | undefined): "success" | "accent" | "neutral" {
  if (state === "released") return "success";
  if (state === "signed_off") return "accent";
  return "neutral";
}

/* ---------- who a GP lead should look at first ---------- */

export const PRIORITY_LABEL: Record<string, string> = {
  urgent: "Urgent review",
  high: "High priority",
  standard: "Standard",
  low: "Low priority",
};

export function priorityTone(
  priority: string,
): "danger" | "warning" | "info" | "success" | "neutral" {
  if (priority === "urgent") return "danger";
  if (priority === "high") return "warning";
  if (priority === "standard") return "info";
  if (priority === "low") return "success";
  return "neutral";
}

export function candidateName(person: { name?: string | null; email?: string | null }): string {
  return person.name ?? person.email ?? "Candidate";
}

/** `missing` is what a missing score reads as; callers that know stations were marked say "No automatic score". */
export function formatScore(score: number | null | undefined, missing = "Not assessed"): string {
  if (score === null || score === undefined || Number.isNaN(score)) return missing;
  return `${Math.round(score)}/100`;
}

export function formatCompletion(rate: number | null | undefined): string {
  if (rate === null || rate === undefined || Number.isNaN(rate)) return "-";
  return `${Math.round(rate * 100)}%`;
}

export function cohortSubtitle(candidate: CohortCandidate): string {
  const parts = [`${candidate.stations_completed}/${candidate.stations_total} stations`];
  if (candidate.assessment_score !== null && candidate.assessment_score !== undefined) {
    parts.push(formatScore(candidate.assessment_score));
  }
  return parts.join(" · ");
}

/* ------------------------------------------------------------------------
 * What a decision needs before anybody puts their name to it.
 *
 * The backend is the authority — `ensure_signable` refuses a sign-off without
 * both — and these are here so the screen can say what is missing before
 * somebody presses the button, rather than after.
 * --------------------------------------------------------------------- */

export function signOffBlockers(input: {
  outcome: string | null;
  rationale: string | null;
}): string[] {
  const blockers: string[] = [];
  if (!input.outcome) blockers.push("An outcome has to be chosen.");
  if (!(input.rationale ?? "").trim()) {
    blockers.push("Write down the reason, so anyone can see why this was decided later.");
  }
  return blockers;
}

/**
 * A decision that is signed off, not yet released, and whose outcome may be sent. A withheld outcome
 * is held back and an inconclusive one is undecided: neither goes to the candidate (R-24).
 */
export function releasable(candidate: Pick<CandidateReport, "decision">): boolean {
  const decision = candidate.decision;
  const heldBack = decision?.assessment_outcome === "withheld" || decision?.assessment_outcome === "inconclusive";
  return Boolean(decision?.signed_off_at) && !decision?.released_at && !heldBack;
}

/**
 * What the stations' own pass rules say about a candidate (R-33), for a lead to start from. Only
 * when every station has been marked against a pass rule; otherwise nothing is proposed. Never
 * chosen for them: the outcome is the lead's decision.
 */
export function suggestedOutcome(candidate: CandidateReport): { outcome: "pass" | "fail"; note: string } | null {
  const stations = candidate.stations ?? [];
  if (stations.length === 0 || stations.some((station) => station.passed == null)) return null;
  const passed = stations.filter((station) => station.passed === true).length;
  return {
    outcome: passed === stations.length ? "pass" : "fail",
    note: `Suggested from the marks: ${passed} of ${stations.length} stations passed. You decide.`,
  };
}

export const UNLINKED_REASON = "has no linked account, so the result cannot be released";

/** One line of a release report: who, and why they were not released. */
export function releaseFailureLine(candidate: CandidateReport | undefined, reason: string): string {
  return `${candidate?.name ?? candidate?.email ?? "A candidate"}: ${reason}`;
}

/** Splits a chosen release into the accounts the server can release and the candidates it cannot name an account for. */
export function splitByAccount(chosen: CandidateReport[]): { traineeIds: string[]; unlinked: CandidateReport[] } {
  const traineeIds: string[] = [];
  const unlinked: CandidateReport[] = [];
  for (const candidate of chosen) {
    if (candidate.trainee_id) traineeIds.push(candidate.trainee_id);
    else unlinked.push(candidate);
  }
  return { traineeIds, unlinked };
}

/**
 * The read-out file's name: the sitting it came from, then what it is.
 *
 * The retiring client took the name off the server's `content-disposition`
 * because the server rendered the document. Here the browser writes the file, so
 * the name is made here — and it is the same shape the old downloads had, so two
 * of them in a Downloads folder still say which exam each belongs to.
 */
export function readoutFilename(readout: SittingReadout): string {
  return `${readout.sitting.sitting_id}-exam-readout.md`;
}

/**
 * The read-out as the markdown document the retiring screen handed over.
 *
 * The platform serves the read-out as the JSON it actually is and renders
 * nothing, so the document is written here. It is built from the same
 * `candidateName`, `formatScore`, `formatCompletion` and `PRIORITY_LABEL` the
 * cohort table on screen uses, which is the only way a file somebody files away
 * and a screen somebody reads can be guaranteed to say the same thing about the
 * same candidate — a second set of formatters is a second opinion.
 */
export function readoutAsMarkdown(readout: SittingReadout, w: AssessWords): string {
  const { sitting, summary } = readout;
  const candidates = readout.candidates ?? [];
  const stamp = (value: string) => new Date(value).toLocaleString("en-GB");
  const lines: string[] = [];

  lines.push(`# ${sitting.name}: examination read-out`, "");
  lines.push(
    `Sitting \`${sitting.sitting_id}\` · organisation \`${readout.org_slug}\` · read-out v${readout.readout_version}`,
    "",
  );
  lines.push(
    `- Scheduled: ${sitting.scheduled_for ? stamp(sitting.scheduled_for) : "not scheduled"}`,
    `- Stations required: ${sitting.required_station_count}`,
    `- Generated: ${stamp(readout.generated_at)}`,
    "",
  );

  lines.push("## Cohort", "", "| Measure | Value |", "| --- | --- |");
  lines.push(`| Cohort size | ${summary.cohort_size} |`);
  lines.push(`| Fully complete | ${summary.fully_complete_count} |`);
  lines.push(`| Average assessment score | ${cell(formatScore(summary.average_assessment_score))} |`);
  lines.push(`| Computed at | ${stamp(summary.computed_at)} |`, "");

  const priorities = Object.entries(summary.priorities ?? {});
  if (priorities.length > 0) {
    lines.push("### Review priorities", "");
    for (const [key, count] of priorities) {
      lines.push(`- ${PRIORITY_LABEL[key] ?? key}: ${count}`);
    }
    lines.push("");
  }

  lines.push("## Candidates", "");
  if (candidates.length === 0) {
    lines.push(w.hiring ? "No candidates were added to this exam." : "Nobody was rostered onto this examination.", "");
  } else {
    lines.push(
      "| Rank | Candidate | Assessment score | Stations | Completion | Review priority |",
      "| --- | --- | --- | --- | --- | --- |",
    );
    for (const candidate of candidates) {
      const row = [
        candidate.rank,
        cell(candidateName(candidate.trainee)),
        cell(formatScore(candidate.assessment_score)),
        `${candidate.stations_completed}/${candidate.stations_total}`,
        cell(formatCompletion(candidate.completion_rate)),
        cell(PRIORITY_LABEL[candidate.review_priority] ?? candidate.review_priority),
      ];
      lines.push(`| ${row.join(" | ")} |`);
    }
    lines.push("");
  }

  const recommendations = readout.recommendations ?? [];
  if (recommendations.length > 0) {
    lines.push("## Recommendations", "");
    for (const item of recommendations) lines.push(`- ${item}`);
    lines.push("");
  }

  lines.push("## Methodology", "", readout.methodology, "");
  return lines.join("\n");
}

/**
 * One markdown table cell.
 *
 * A pipe in a name ends the cell early and shifts every column after it, and
 * names and priorities arrive from people and from data rather than from us.
 */
function cell(value: string): string {
  return value.replace(/\|/g, "\\|").replace(/\r?\n/g, " ");
}

/**
 * Why the backend skipped one candidate in a bulk release, for the lead.
 *
 * The bulk answer carries each refusal's code, not its message.
 */
export function releaseRefusal(code: string): string {
  switch (code) {
    case "evidence_changed":
      return "the marking changed after sign-off, so sign it off again";
    case "invalid_workflow":
      return "not signed off yet, or already released";
    case "outcome_not_releasable":
      return "a withheld or inconclusive outcome is not sent to the candidate";
    case "decision_revised":
      return "the decision was changed by somebody else; reload and check it";
    case "result_not_found":
      return "no decision recorded";
    default:
      return `refused (${code})`;
  }
}

/** "3 of 5 marked", or "Not started" while there is nothing to count. */
export function countNote(done: number, total: number, word: string): string {
  return total === 0 ? "Not started" : `${done} of ${total} ${word}`;
}

type DecisionCounts = { not_decided: number; draft: number; signed_off: number; released?: number; sat?: number };

/**
 * Candidates who sat and have no decision yet. Someone who never sat needs none (the decision API
 * refuses `candidate_did_not_sit`), so the server's `sat` caps the undecided count; a row without
 * `sat` keeps the server's `not_decided`.
 */
export function undecided(row: DecisionCounts): number {
  if (row.sat === undefined) return row.not_decided;
  const decided = row.draft + row.signed_off + (row.released ?? 0);
  return Math.min(row.not_decided, Math.max(row.sat - decided, 0));
}

export type ResultsTab = "needs_decision" | "ready_to_release" | "all";

/** The results-index rows a tab shows: work still to decide, decisions waiting to go out, or everything. */
export function filterResultsRows<T extends DecisionCounts & { mode?: string }>(
  rows: T[],
  tab: ResultsTab,
): T[] {
  // A training sitting records no decisions, so it never waits on one.
  const decides = (row: T) => row.mode !== "training";
  if (tab === "needs_decision") return rows.filter((row) => decides(row) && (undecided(row) > 0 || row.draft > 0));
  if (tab === "ready_to_release") return rows.filter((row) => decides(row) && row.signed_off > 0);
  return rows;
}

/** The results index's date column: "Today", "28 Oct", or "Not scheduled". */
export function resultsDate(iso: string | null | undefined, now: Date = new Date()): string {
  const words = sittingWhen(iso, now);
  return words.startsWith("Today") ? "Today" : words;
}

/** One line under "Needs your attention" on the results index. */
export type AttentionItem = { key: string; text: string; action: "Decide" | "Release" | "Mark"; path: string };

const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/**
 * Work waiting on this person: decisions to make, then decisions to release, then the stations the
 * supervisor has not marked. Built from the index's own counts, so it needs no read of its own.
 */
export function attentionItems(
  rows: (DecisionCounts & { sitting_id: string; name: string; mode?: string })[],
  unmarked: UnmarkedStation[],
): AttentionItem[] {
  const decide: AttentionItem[] = [];
  const release: AttentionItem[] = [];
  for (const row of rows) {
    if (row.mode === "training") continue;
    const path = `/sittings/${row.sitting_id}/results`;
    const waiting = undecided(row);
    if (waiting > 0) {
      decide.push({
        key: `decide-${row.sitting_id}`,
        text: `${row.name}: ${count(waiting, "candidate needs", "candidates need")} a decision`,
        action: "Decide",
        path,
      });
    } else if (row.draft > 0) {
      decide.push({
        key: `draft-${row.sitting_id}`,
        text: `${row.name}: ${count(row.draft, "decision is", "decisions are")} in draft, waiting to be signed off`,
        action: "Decide",
        path,
      });
    }
    if (row.signed_off > 0) {
      release.push({
        key: `release-${row.sitting_id}`,
        text: `${row.name}: ${count(row.signed_off, "result", "results")} signed off and not yet released`,
        action: "Release",
        path,
      });
    }
  }
  const items = [...decide, ...release];
  if (unmarked[0]) {
    items.push({
      key: "mark",
      text: `${count(unmarked.length, "station", "stations")} waiting for your marks`,
      action: "Mark",
      path: slotReviewPath(unmarked[0]),
    });
  }
  return items;
}

/** The hire decisions tiles: how many are hired, on the reserve list, not hired, and still to decide (withdrawn is none of these). */
export function hiringTally(candidates: readonly { decision?: { recruitment_outcome?: string | null } | null }[]): {
  hired: number;
  reserve: number;
  notHired: number;
  stillToDecide: number;
} {
  const tally = { hired: 0, reserve: 0, notHired: 0, stillToDecide: 0 };
  for (const candidate of candidates) {
    const outcome = candidate.decision?.recruitment_outcome;
    if (outcome === "hired") tally.hired += 1;
    else if (outcome === "reserve") tally.reserve += 1;
    else if (outcome === "not_hired") tally.notHired += 1;
    else if (!outcome || outcome === "pending") tally.stillToDecide += 1;
  }
  return tally;
}
