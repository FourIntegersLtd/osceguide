import assert from "node:assert/strict";
import test from "node:test";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import {
  cancelMenuLabel,
  cancelMessage,
  candidatesEmptyBody,
  circuitsEmpty,
  editLabel,
  moreCircuitsLine,
} from "@/domains/assess/sittingCopy";

test("an institution keeps its sitting words", () => {
  assert.deepEqual(circuitsEmpty(INSTITUTION_WORDS), { title: "No circuits yet", body: "Add at least one circuit so candidates can take this sitting." });
  assert.equal(candidatesEmptyBody(INSTITUTION_WORDS), "Add a circuit to put people on this sitting.");
  assert.equal(moreCircuitsLine(2, INSTITUTION_WORDS), "2 more circuits · supervisors see their own circuit first");
  assert.equal(editLabel(INSTITUTION_WORDS), "Edit");
  assert.equal(cancelMenuLabel(INSTITUTION_WORDS), "Cancel sitting");
  assert.equal(cancelMessage(INSTITUTION_WORDS), "Nobody can take it once it is cancelled. Nothing has started, so no attempt is lost.");
});

test("an employer reads rotations and assessments", () => {
  assert.deepEqual(circuitsEmpty(EMPLOYER_WORDS), { title: "No rotations yet", body: "Add at least one rotation so candidates can take this assessment." });
  assert.equal(candidatesEmptyBody(EMPLOYER_WORDS), "Add a rotation to put candidates on this assessment.");
  assert.equal(moreCircuitsLine(6, EMPLOYER_WORDS), "6 more rotations");
  assert.equal(editLabel(EMPLOYER_WORDS), "Edit details");
  assert.equal(cancelMenuLabel(EMPLOYER_WORDS), "Cancel this assessment");
  assert.match(cancelMessage(EMPLOYER_WORDS), /Candidates and assessors are told by email\.$/);
});
