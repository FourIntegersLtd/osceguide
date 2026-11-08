import assert from "node:assert/strict";
import test from "node:test";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import { SCHEDULE_STEPS, supervisorOptions, scheduleSteps, scheduleSubmitLabel, scheduleIntro, scheduleReviewLabels } from "@/domains/assess/scheduleSitting";

test("institution words leave the steps byte-identical", () => {
  assert.deepEqual(scheduleSteps(INSTITUTION_WORDS), SCHEDULE_STEPS);
  assert.equal(scheduleSubmitLabel(INSTITUTION_WORDS), "Create sitting");
  assert.equal(scheduleIntro(INSTITUTION_WORDS), "Steps unlock in order. Nothing is created until the last step.");
});

test("hire steps read the employer board", () => {
  const steps = scheduleSteps(EMPLOYER_WORDS);
  assert.deepEqual(steps.map((s) => s.id), SCHEDULE_STEPS.map((s) => s.id));
  assert.deepEqual(steps.map((s) => s.label), ["Exam and name", "Stations", "Candidates", "Rotations", "Assessors", "Check and schedule"]);
  assert.equal(steps[2]?.title, "Who is sitting it?");
  assert.equal(steps[2]?.desc, "Pick an intake, pick candidates one by one, or paste their emails.");
  assert.equal(steps[3]?.desc, "A rotation is one candidate going through every station in turn. We build them from your choices; change the times or breaks if you need to.");
  assert.equal(steps[4]?.title, "Who assesses?");
  assert.equal(steps[5]?.title, "Check and schedule");
});

test("hire intro, last button and review labels", () => {
  assert.equal(scheduleIntro(EMPLOYER_WORDS), "Nothing is created until you press Schedule on the last step.");
  assert.equal(scheduleSubmitLabel(EMPLOYER_WORDS), "Schedule");
  assert.deepEqual(scheduleReviewLabels(EMPLOYER_WORDS), { year: "Intake", supervisor: "Assessors" });
  assert.deepEqual(scheduleReviewLabels(INSTITUTION_WORDS), { year: "Year group", supervisor: "Supervisor" });
});

test("hire names the assessor options in its words, institution keeps its own", () => {
  assert.deepEqual(supervisorOptions(EMPLOYER_WORDS).map((o) => o.title), ["One assessor for every rotation", "An assessor for each candidate"]);
});
