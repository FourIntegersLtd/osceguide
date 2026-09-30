import assert from "node:assert/strict";
import test, { describe, it } from "node:test";
import type { CandidateReport, SittingReadout, StationReport } from "@/domains/assess/results/api";
import {
  releaseRefusal,
  ASSESSMENT_OUTCOMES,
  evidenceFor,
  outcomeTone,
  readoutAsMarkdown,
  readoutFilename,
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

/* ---------- the examination read-out, as a file ---------- */

function readout(over: Partial<SittingReadout> = {}): SittingReadout {
  return {
    org_slug: "kings",
    readout_version: "1",
    generated_at: "2026-09-24T09:00:00Z",
    methodology: "The worst rating wins per domain.",
    recommendations: ["Speak to the candidate marked incomplete."],
    sitting: {
      sitting_id: "s1",
      name: "Autumn sitting",
      required_station_count: 8,
      scheduled_for: null,
    },
    summary: {
      cohort_size: 2,
      fully_complete_count: 1,
      average_assessment_score: 71.5,
      computed_at: "2026-09-24T09:00:00Z",
      priorities: { high: 1 },
    },
    candidates: [
      {
        rank: 1,
        assessment_score: 82,
        completion_rate: 1,
        review_priority: "low",
        stations_completed: 8,
        stations_total: 8,
        trainee: { user_id: "u1", name: "Amara Okafor", email: null, trainee_id: null },
      },
      {
        rank: 2,
        assessment_score: null,
        completion_rate: 0.5,
        review_priority: "high",
        stations_completed: 4,
        stations_total: 8,
        trainee: { user_id: "u2", name: "Rowan | Pipe", email: null, trainee_id: null },
      },
    ],
    ...over,
  } as SittingReadout;
}

test("the read-out is the markdown document the retiring screen handed over", () => {
  const document = readoutAsMarkdown(readout());

  assert.match(document, /^# Autumn sitting — examination read-out\n/);
  assert.ok(document.includes("## Cohort"), document);
  assert.ok(document.includes("| Cohort size | 2 |"), document);
  assert.ok(document.includes("## Candidates"), document);
  assert.ok(document.includes("| 1 | Amara Okafor |"), document);
  assert.ok(document.includes("| 8/8 |"), document);
  assert.ok(document.includes("### Review priorities"), document);
  assert.ok(document.includes("## Recommendations"), document);
  assert.ok(document.includes("- Speak to the candidate marked incomplete."), document);
  assert.ok(document.includes("## Methodology"), document);
  assert.ok(document.includes("The worst rating wins per domain."), document);
});

test("a pipe in somebody's name cannot shift every column after it", () => {
  // Names come from people, and an unescaped pipe ends the cell early — which
  // in a document somebody files away is a silently wrong table, not a crash.
  assert.ok(readoutAsMarkdown(readout()).includes("Rowan \\| Pipe"));
});

test("an examination nobody sat still renders a document", () => {
  const document = readoutAsMarkdown(readout({ candidates: [] }));
  assert.ok(document.includes("Nobody was rostered onto this examination."), document);
  assert.ok(!document.includes("| Rank |"), document);
});

test("the file is named for what it now is", () => {
  assert.equal(readoutFilename(readout()), "s1-exam-readout.md");
});

describe("why a bulk release skipped somebody", () => {
  it("says what to do about marking that moved", () => {
    assert.match(releaseRefusal("evidence_changed"), /sign it off again/);
  });

  it("names an unknown refusal by its code rather than hiding it", () => {
    assert.equal(releaseRefusal("something_new"), "refused (something_new)");
  });
});
