import assert from "node:assert/strict";
import test from "node:test";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import { decidable, nextUndecided, saveNextLabel, sheetSignature, showsHiringDecision, signedOffByLine, trainingNotice } from "@/domains/assess/results/hireDecisions";

const person = (user_id: string, outcome: string | null, trainee_id: string | null = `t-${user_id}`) => ({
  user_id,
  trainee_id,
  decision: outcome ? { recruitment_outcome: outcome } : null,
});

test("hiring decisions show only for an employer on a formal exam; Training hides them", () => {
  assert.equal(showsHiringDecision("exam", EMPLOYER_WORDS), true);
  assert.equal(showsHiringDecision("training", EMPLOYER_WORDS), false);
  assert.equal(showsHiringDecision("exam", INSTITUTION_WORDS), false);
});

test("the Training assessment says why there is no hiring decision", () => {
  assert.deepEqual(trainingNotice("training", EMPLOYER_WORDS), {
    title: "This was a Training assessment",
    body: "Training gives candidates feedback only, so there are no hiring decisions. Sign off and release the results as usual.",
  });
  assert.equal(trainingNotice("exam", EMPLOYER_WORDS), null);
  assert.equal(trainingNotice("training", INSTITUTION_WORDS), null);
});

test("Save and next goes to the next candidate still to decide, then wraps, then stops", () => {
  const list = [person("a", "hired"), person("b", null), person("c", "not_hired"), person("d", null)];
  assert.equal(nextUndecided(list, "a")?.user_id, "b");
  assert.equal(nextUndecided(list, "b")?.user_id, "d");
  assert.equal(nextUndecided(list, "d")?.user_id, "b");
  assert.equal(nextUndecided([person("a", null), person("b", "hired")], "a"), null);
  assert.equal(nextUndecided([person("a", null), person("x", null, null)], "a"), null);
});

test("the save button names what it does", () => {
  assert.equal(saveNextLabel(true), "Save draft and next candidate");
  assert.equal(saveNextLabel(false), "Save draft");
});

test("a Pass with no hiring decision is still to decide; a pending one too", () => {
  const passed = (user_id: string, recruitment_outcome: string | null) => ({
    user_id,
    trainee_id: `t-${user_id}`,
    decision: { assessment_outcome: "pass", recruitment_outcome },
  });
  const list = [passed("a", "hired"), passed("b", null), passed("c", "pending")];
  assert.equal(nextUndecided(list, "a")?.user_id, "b");
  assert.equal(nextUndecided(list, "b")?.user_id, "c");
});

test("an institution's exam-mode results carry no hiring decision, tiles or notice", () => {
  assert.equal(showsHiringDecision("exam", INSTITUTION_WORDS), false);
  assert.equal(trainingNotice("exam", INSTITUTION_WORDS), null);
});

import {
  hireResultsSubtitle,
  releasedSummary,
  releaseResultsLabel,
  resultOverrideHelper,
  signOffGate,
  stationVerdict,
} from "@/domains/assess/results/hireDecisions";

test("the decisions subtitle, sign-off gate and release words are the board's", () => {
  assert.equal(hireResultsSubtitle("2026-10-14T12:00:00Z", 10), "Formal exam · 14 Oct · 10 candidates. Decide each candidate, sign off, then release.");
  assert.equal(hireResultsSubtitle(null, 1), "Formal exam · 1 candidate. Decide each candidate, sign off, then release.");
  assert.equal(signOffGate(10, 3), "Sign off needs a decision for all 10 candidates. 3 are left.");
  assert.equal(signOffGate(10, 1), "Sign off needs a decision for all 10 candidates. 1 is left.");
  assert.equal(signOffGate(10, 0), null);
  assert.equal(releaseResultsLabel(10), "Release results to 10 candidates");
  assert.equal(releasedSummary(10, { hired: 5, reserve: 3, notHired: 2 }), "10 candidates have been told. Hired 5 · Reserve list 3 · Not hired 2.");
  assert.equal(resultOverrideHelper(4, 5), "From the marking: 4 of 5 stations passed. Change it only with a reason.");
  assert.equal(stationVerdict(true), "Pass");
  assert.equal(stationVerdict(false), "Fail");
  assert.equal(stationVerdict(null), null);
});

const signed = (trainee_id: string | null, at: string | null, name: string | null = "Joy Okafor") => ({
  trainee_id,
  decision: at ? { signed_off_at: at, signed_off_by_name: name } : null,
});

test("the sheet is signed once every candidate who can be decided is signed off", () => {
  const early = new Date(2026, 10, 8, 14, 2).toISOString();
  const late = new Date(2026, 10, 8, 14, 5).toISOString();
  assert.deepEqual(sheetSignature([signed("a", early), signed("b", late, "Sara Khan"), signed(null, null)]), { name: "Sara Khan", at: late });
  assert.equal(sheetSignature([signed("a", early), signed("b", null)]), null);
  assert.equal(sheetSignature([]), null);
});

test("the signed-off line names who and when, today or on an earlier day", () => {
  const now = new Date(2026, 10, 8, 18, 0);
  const at = new Date(2026, 10, 8, 14, 2).toISOString();
  assert.equal(signedOffByLine({ name: "Joy Okafor", at }, now), "Signed off by Joy Okafor, today 14:02");
  assert.equal(signedOffByLine({ name: null, at }, now), "Signed off, today 14:02");
  assert.equal(signedOffByLine({ name: "Joy Okafor", at: new Date(2026, 9, 14, 9, 30).toISOString() }, now), "Signed off by Joy Okafor, 14 Oct 09:30");
});

test("decidable leaves out a candidate who sat no station, and the sheet signature ignores them", () => {
  const sat = { user_id: "a", trainee_id: "t1", stations: [{ absent: false }] };
  const absent = { user_id: "b", trainee_id: "t2", stations: [{ absent: true }] };
  assert.deepEqual(decidable([sat, absent]), [sat]);
  assert.deepEqual(sheetSignature([{ ...sat, decision: { signed_off_at: "2026-10-14T09:30:00Z", signed_off_by_name: "Joy Okafor" } }, absent]), { name: "Joy Okafor", at: "2026-10-14T09:30:00Z" });
});
