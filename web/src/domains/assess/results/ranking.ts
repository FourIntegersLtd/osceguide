import type { CandidateReport } from "@/domains/assess/results/api";

export type RankedCandidate = { rank: number | null; candidate: CandidateReport };

/**
 * Best first, for comparing candidates at a hiring decision. Score first, then stations passed;
 * equal on both share a rank and the next rank skips (1, 1, 3). Nobody with no score is ranked.
 */
export function rankCandidates(candidates: readonly CandidateReport[]): RankedCandidate[] {
  const scored = candidates.filter((c) => c.score != null);
  const unscored = candidates.filter((c) => c.score == null);
  const sorted = [...scored].sort(
    (a, b) => (b.score as number) - (a.score as number) || b.stations_passed - a.stations_passed,
  );
  const ranked = sorted.map((candidate, at) => {
    const before = sorted[at - 1];
    const tied = before && before.score === candidate.score && before.stations_passed === candidate.stations_passed;
    return { candidate, rank: tied ? -1 : at + 1 };
  });
  // A tie takes the rank of the one above it.
  ranked.forEach((row, at) => {
    if (row.rank === -1) row.rank = ranked[at - 1]?.rank ?? at + 1;
  });
  return [...ranked, ...unscored.map((candidate) => ({ candidate, rank: null }))];
}

/** What a decision still needs before it can be saved: a hire is never recorded without its reason. */
export function decisionBlockers(input: { recruitment: string; rationale: string | null }): string[] {
  return input.recruitment === "hired" && !(input.rationale ?? "").trim() ? ["Say why you are hiring this candidate."] : [];
}
