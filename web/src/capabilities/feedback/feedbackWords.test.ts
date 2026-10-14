import assert from "node:assert/strict";
import { test } from "node:test";
import { coverageSummary, gradeTallyText, gradeWord } from "./feedbackWords";

test("a grade is named by its tone, never by its letter", () => {
  assert.equal(gradeWord("G", "good"), "Good");
  assert.equal(gradeWord("R", "poor"), "Poor");
  assert.equal(gradeWord("B", null), "B");
});

test("a grade tally says what was counted, in words", () => {
  assert.equal(gradeTallyText(2, "G", "good"), "2 competencies graded Good");
  assert.equal(gradeTallyText(1, "A", "fair"), "1 competency graded Fair");
  assert.equal(gradeTallyText(3, "R", null), "3 competencies graded R");
});

test("a grade nobody got is not shown", () => {
  assert.equal(gradeTallyText(0, "G", "good"), null);
});

test("coverage says where it was covered, and counts only what was fully covered", () => {
  assert.equal(coverageSummary(3, 5), "3 of 5 items fully covered during the consultation");
  assert.equal(coverageSummary(1, 1), "The item was fully covered during the consultation");
  assert.equal(coverageSummary(5, 5), "All 5 items fully covered during the consultation");
  assert.equal(coverageSummary(0, 4), "None of the 4 items fully covered during the consultation");
});

test("a single item that was not covered is not called covered", () => {
  assert.equal(coverageSummary(0, 1), "The item was not fully covered during the consultation");
});
