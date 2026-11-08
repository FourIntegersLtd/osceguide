import assert from "node:assert/strict";
import test from "node:test";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import { say } from "@/domains/assess/roster/rosterWords";

test("an institution reads its roster sentences unchanged", () => {
  const text = "That person has already set up their account. Create a year group for the trainees on the roster.";
  assert.equal(say(INSTITUTION_WORDS, text), text);
});

test("hire says candidate and intake where the roster says trainee and year group", () => {
  assert.equal(say(EMPLOYER_WORDS, "Change their name, email or year group."), "Change their name, email or intake.");
  assert.equal(say(EMPLOYER_WORDS, "Delete a trainee. 3 people in the Year group."), "Delete a candidate. 3 candidates in the Intake.");
  assert.equal(say(EMPLOYER_WORDS, "Groups and year groups"), "Groups and intakes");
});

test("hire words the sitting phrases whole, never as an assessment", () => {
  assert.equal(say(EMPLOYER_WORDS, "Stop them sitting or signing in. Their records are kept."), "Stop them taking assessments or signing in. Their records are kept.");
  assert.equal(say(EMPLOYER_WORDS, "Ana will not be able to sign in or sit anything."), "Ana will not be able to sign in or take any assessment.");
  assert.equal(say(EMPLOYER_WORDS, "a@b.co is already on this roster."), "a@b.co is already a candidate.");
  assert.equal(say(EMPLOYER_WORDS, "Nobody is on the roster yet."), "Nobody is on the candidate list yet.");
});
