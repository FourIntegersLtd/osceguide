import assert from "node:assert/strict";
import test from "node:test";
import type { CandidateReport, StationReport } from "@/domains/assess/results/api";
import {
  ASSESSMENT_OUTCOMES,
  evidenceFor,
  outcomeTone,
  releasable,
  signOffBlockers,
  workflowLabel,
} from "@/domains/assess/results/support";

function station(over: Partial<StationReport> & { slot_id: string }): StationReport {
  return {
    circuit_id: "c1",
    circuit_name: "Morning circuit",
    slot_index: 0,
    station_title: "Hip pain",
    slot_status: "completed",
    attempt_status: "evaluated",
    marked: true,
    overall_rag: "G",
    by_domain: {},
    ...over,
  } as StationReport;
}

function candidate(over: Partial<CandidateReport> = {}): CandidateReport {
  return {
    user_id: "u1",
    trainee_id: "t1",
    name: "Amara Okafor",
    email: "amara@example.com",
    stations: [],
    stations_marked: 0,
    overall_rag: null,
    decision: null,
    ...over,
  } as CandidateReport;
}

test("the outcomes offered are the four the backend accepts", () => {
  // "borderline" was offered by the rebuilt screen and is a 422 on save.
  assert.deepEqual([...ASSESSMENT_OUTCOMES], ["pass", "fail", "inconclusive", "withheld"]);
  assert.ok(!ASSESSMENT_OUTCOMES.includes("borderline" as never));
});

test("an unresolved outcome does not read as a pass or a fail", () => {
  assert.equal(outcomeTone("pass"), "success");
  assert.equal(outcomeTone("fail"), "danger");
  assert.equal(outcomeTone("inconclusive"), "warning");
  assert.equal(outcomeTone("withheld"), "warning");
  assert.equal(outcomeTone(null), "neutral");
});

test("sign-off is blocked until there is both an outcome and a reason", () => {
  assert.equal(signOffBlockers({ outcome: "pass", rationale: "Met the standard." }).length, 0);
  assert.equal(signOffBlockers({ outcome: null, rationale: "Met it." }).length, 1);
  // Whitespace is not a rationale.
  assert.equal(signOffBlockers({ outcome: "pass", rationale: "   " }).length, 1);
  assert.equal(signOffBlockers({ outcome: null, rationale: null }).length, 2);
});

test("the evidence is the marking, and the same marking hashes the same", () => {
  const one = candidate({
    stations_marked: 2,
    overall_rag: "A",
    stations: [station({ slot_id: "b", overall_rag: "A" }), station({ slot_id: "a" })],
  });
  const other = candidate({
    stations_marked: 2,
    overall_rag: "A",
    // Same stations, arriving the other way round.
    stations: [station({ slot_id: "a" }), station({ slot_id: "b", overall_rag: "A" })],
  });
  assert.deepEqual(evidenceFor(one), evidenceFor(other));
});

test("a station re-marked after sign-off changes the evidence", () => {
  const before = candidate({ stations: [station({ slot_id: "a", overall_rag: "G" })] });
  const after = candidate({ stations: [station({ slot_id: "a", overall_rag: "R" })] });
  assert.notDeepEqual(evidenceFor(before), evidenceFor(after));
});

test("only a signed-off decision that is not yet out can be released", () => {
  assert.equal(releasable(candidate()), false);
  assert.equal(
    releasable(
      candidate({
        decision: {
          workflow_state: "signed_off",
          assessment_outcome: "pass",
          recruitment_outcome: null,
          signed_off_at: "2026-09-19T09:00:00Z",
          released_at: null,
        },
      }),
    ),
    true,
  );
  assert.equal(
    releasable(
      candidate({
        decision: {
          workflow_state: "released",
          assessment_outcome: "pass",
          recruitment_outcome: null,
          signed_off_at: "2026-09-19T09:00:00Z",
          released_at: "2026-09-19T10:00:00Z",
        },
      }),
    ),
    false,
  );
});

test("a decision nobody has started is not called a draft", () => {
  assert.equal(workflowLabel(null), "Not started");
  assert.equal(workflowLabel("signed_off"), "Signed off");
});
