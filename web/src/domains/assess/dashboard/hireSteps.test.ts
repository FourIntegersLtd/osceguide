import assert from "node:assert/strict";
import test from "node:test";
import type { OrgSetup } from "@/domains/assess/dashboard/api";
import { hireSetupComplete, hireSetupSteps, nextHireStep } from "@/domains/assess/dashboard/hireSteps";
import { EMPLOYER_WORDS } from "@/domains/assess/vocabulary";

function setup(over: Partial<OrgSetup> = {}): OrgSetup {
  return {
    programme_exam_rubric_ready: false,
    ready_to_run: false,
    sitting_scheduled: false,
    stations_available: false,
    team_invited: false,
    trainees_added: false,
    ...over,
  } as OrgSetup;
}

test("a new employer sees four steps in the board's order, none done", () => {
  const steps = hireSetupSteps(setup(), EMPLOYER_WORDS);
  assert.deepEqual(steps.map((s) => [s.id, s.label, s.state]), [
    ["exam", "Exam", "todo"],
    ["candidates", "Candidates", "todo"],
    ["assessors", "Assessors", "todo"],
    ["assessment", "Assessment", "todo"],
  ]);
  assert.equal(nextHireStep(steps)?.id, "exam");
});

test("each step is done from the flag the dashboard already returns", () => {
  const steps = hireSetupSteps(
    setup({ programme_exam_rubric_ready: true, stations_available: true, trainees_added: true }),
    EMPLOYER_WORDS,
  );
  assert.deepEqual(steps.map((s) => s.state), ["done", "done", "todo", "todo"]);
  assert.equal(nextHireStep(steps)?.id, "assessors");
});

test("an exam with no published station is not done", () => {
  const steps = hireSetupSteps(setup({ programme_exam_rubric_ready: true }), EMPLOYER_WORDS);
  assert.equal(steps[0]?.state, "todo");
});

test("the next step names its screen and uses the employer's words", () => {
  const next = nextHireStep(
    hireSetupSteps(setup({ programme_exam_rubric_ready: true, stations_available: true }), EMPLOYER_WORDS),
  );
  assert.equal(next?.title, "Add your candidates");
  assert.equal(next?.cta, "Add candidates");
  assert.equal(next?.href, "/trainees");
});

test("each step links to the screen that fills it", () => {
  const hrefs = hireSetupSteps(setup(), EMPLOYER_WORDS).map((s) => s.href);
  assert.deepEqual(hrefs, ["/authoring/exams/new", "/trainees", "/team", "/sittings/new"]);
});

test("the checklist is over once exam, candidates and an assessment exist; inviting assessors never holds it open", () => {
  const done = setup({ programme_exam_rubric_ready: true, stations_available: true, trainees_added: true, sitting_scheduled: true });
  assert.equal(hireSetupComplete(hireSetupSteps(done, EMPLOYER_WORDS)), true);
  assert.equal(hireSetupComplete(hireSetupSteps({ ...done, sitting_scheduled: false }, EMPLOYER_WORDS)), false);
  assert.equal(hireSetupComplete(hireSetupSteps(setup(), EMPLOYER_WORDS)), false);
});

test("with every step done there is no next step", () => {
  const all = setup({ programme_exam_rubric_ready: true, stations_available: true, trainees_added: true, team_invited: true, sitting_scheduled: true });
  assert.equal(nextHireStep(hireSetupSteps(all, EMPLOYER_WORDS)), null);
});
