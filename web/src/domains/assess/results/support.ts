import type { CandidateReport, CohortCandidate, Evidence } from "@/domains/assess/results/api";

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

export const OUTCOME_LABEL: Record<AssessmentOutcome, string> = {
  pass: "Pass",
  fail: "Fail",
  inconclusive: "Inconclusive",
  withheld: "Withheld",
};

export const OUTCOME_HINT: Record<AssessmentOutcome, string> = {
  pass: "Met the standard.",
  fail: "Did not meet the standard.",
  inconclusive: "Not enough was assessed to decide.",
  withheld: "Decided, and not being released — an investigation, an appeal.",
};

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
  if (!state) return "Not started";
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

export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined || Number.isNaN(score)) return "Not assessed";
  return `${Math.round(score)}/100`;
}

export function formatCompletion(rate: number | null | undefined): string {
  if (rate === null || rate === undefined || Number.isNaN(rate)) return "—";
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
 * The evidence.
 *
 * What the outcome was judged against, sent with the draft and again at
 * release. The backend fingerprints it at sign-off and refuses a release whose
 * evidence no longer matches — a station re-marked in between would otherwise
 * send a candidate an outcome nobody approved.
 *
 * The retiring client never sent any, so that check compared two empty objects
 * and passed every time. Only the marking goes in: the shape has to be stable,
 * or an unrelated edit elsewhere in the report would read as tampering.
 * --------------------------------------------------------------------- */

export function evidenceFor(candidate: CandidateReport): Evidence {
  const stations = (candidate.stations ?? [])
    .map((station) => ({
      slot_id: station.slot_id,
      marked: station.marked,
      overall_rag: station.overall_rag ?? null,
    }))
    .sort((a, b) => a.slot_id.localeCompare(b.slot_id));

  return {
    stations,
    stations_marked: candidate.stations_marked,
    overall_rag: candidate.overall_rag ?? null,
  };
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
    blockers.push("A rationale has to be written — somebody has to be able to say why, later.");
  }
  return blockers;
}

/** A candidate whose sign-off is done and whose release is not. */
export function releasable(candidate: CandidateReport): boolean {
  const decision = candidate.decision;
  return Boolean(decision?.signed_off_at) && !decision?.released_at;
}
