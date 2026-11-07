import assert from "node:assert/strict";
import test from "node:test";
import type { CandidateReport } from "@/domains/assess/results/api";
import { decisionBlockers, rankCandidates } from "@/domains/assess/results/ranking";

const c = (id: string, score: number | null, passed = 0, name = id): CandidateReport =>
  ({ user_id: id, name, email: null, score, stations_passed: passed, stations_marked: score === null ? 0 : 5, decision: null }) as unknown as CandidateReport;

test("best score first, ties share a rank and the next rank skips", () => {
  const ranked = rankCandidates([c("a", 60), c("b", 80), c("c", 80), c("d", 40)]);
  assert.deepEqual(ranked.map((r) => [r.candidate.user_id, r.rank]), [["b", 1], ["c", 1], ["a", 3], ["d", 4]]);
});

test("equal displayed scores share a rank, whatever sits behind the rounding", () => {
  // 79.6 and 80.4 both read 80/100; 79.4 reads 79/100.
  const ranked = rankCandidates([c("a", 80.4, 2), c("b", 79.6, 2), c("c", 79.4, 2)]);
  assert.deepEqual(ranked.map((r) => [r.candidate.user_id, r.rank]), [["a", 1], ["b", 1], ["c", 3]]);
});

test("more stations passed breaks a tie on score", () => {
  const ranked = rankCandidates([c("a", 70, 3), c("b", 70, 5)]);
  assert.deepEqual(ranked.map((r) => [r.candidate.user_id, r.rank]), [["b", 1], ["a", 2]]);
});

test("someone with no score yet is listed last and unranked", () => {
  const ranked = rankCandidates([c("a", null), c("b", 50)]);
  assert.deepEqual(ranked.map((r) => [r.candidate.user_id, r.rank]), [["b", 1], ["a", null]]);
});

test("a hire needs a reason before it can be saved; other outcomes do not", () => {
  assert.deepEqual(decisionBlockers({ recruitment: "hired", rationale: "  " }), ["Say why you are hiring this candidate."]);
  assert.deepEqual(decisionBlockers({ recruitment: "hired", rationale: "Strongest on safety netting." }), []);
  assert.deepEqual(decisionBlockers({ recruitment: "reserve", rationale: "" }), []);
  assert.deepEqual(decisionBlockers({ recruitment: "", rationale: "" }), []);
});
