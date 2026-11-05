import assert from "node:assert/strict";
import test from "node:test";
import type { ResultsIndexRow } from "@/domains/assess/results/api";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/domains/assess/vocabulary";
import type { LiveCircuit, OrgSetup } from "@/domains/assess/dashboard/api";
import {
  runsByDay,
  boardOrder,
  candidatesLabel,
  circuitStatus,
  assistantSteps,
  attentionFromResults,
  firstOpenStep,
  recordingMissing,
  setupComplete,
  todaySentence,
  stepBlock,
  runningLine,
  stillToReviewLine,
  circuitsBySitting,
  dateEyebrow,
  dateTile,
} from "@/domains/assess/dashboard/support";

function setup(over: Partial<OrgSetup> = {}): OrgSetup {
  return {
    rubric_published: false,
    exam_published: false,
    template_published: false,
    sitting_scheduled: false,
    trainees_added: false,
    stations_available: false,
    team_invited: false,
    programme_exam_rubric_ready: false,
    ready_to_run: false,
    ...over,
  };
}

function circuit(over: Partial<LiveCircuit> & { circuit_id: string }): LiveCircuit {
  return {
    circuit_name: `Circuit ${over.circuit_id}`,
    sitting_id: "s1",
    sitting_name: "June sitting",
    mode: "exam",
    room_name: "room-1",
    supervisor: null,
    candidates: [],
    current_station: null,
    phase: "simulation",
    phase_started_at: null,
    phase_ends_at: null,
    paused: false,
    auto_advance: true,
    elapsed_seconds: 0,
    remaining_seconds: 600,
    stations_total: 5,
    stations_completed: 1,
    attempt_id: "a1",
    attempt_status: "running",
    alerts: [],
    ...over,
  } as LiveCircuit;
}

test("a fresh organisation sees the five steps, in order, none done, the supervisor one optional", () => {
  assert.deepEqual(
    assistantSteps(setup(), INSTITUTION_WORDS).map((step) => [step.id, step.label, step.done, step.optional, step.cta, step.href]),
    [
      ["exam", "Set up an exam", false, false, "Set up an exam", "/authoring/exams/new"],
      ["stations", "Add stations", false, false, "Add a station", "/authoring/stations"],
      ["trainees", "Add trainees", false, false, "Add trainees", "/trainees"],
      ["supervisor", "Invite a supervisor", false, true, "Invite staff", "/team"],
      ["sitting", "Schedule your first sitting", false, false, "Schedule a sitting", "/sittings/new"],
    ],
  );
});

test("hire reads its own words in the steps", () => {
  const steps = assistantSteps(setup(), EMPLOYER_WORDS);
  assert.deepEqual(
    [steps[2]?.title, steps[3]?.title, steps[4]?.cta],
    ["Add your candidates", "Invite an assessor", "Schedule an assessment"],
  );
});

test("the first open step leads, and setup ends when the required steps are done", () => {
  assert.equal(firstOpenStep(assistantSteps(setup(), INSTITUTION_WORDS)), 0);
  assert.equal(firstOpenStep(assistantSteps(setup({ programme_exam_rubric_ready: true, stations_available: true }), INSTITUTION_WORDS)), 2);
  const done = setup({ programme_exam_rubric_ready: true, stations_available: true, trainees_added: true, sitting_scheduled: true });
  // The supervisor step is optional: it does not hold setup open.
  assert.equal(setupComplete(assistantSteps(done, INSTITUTION_WORDS)), true);
  assert.equal(setupComplete(assistantSteps(setup({ trainees_added: true }), INSTITUTION_WORDS)), false);
});

test("scheduling is blocked, with the fix, until an exam is ready", () => {
  const sitting = assistantSteps(setup(), INSTITUTION_WORDS).find((step) => step.id === "sitting");
  assert.ok(sitting);
  assert.deepEqual(stepBlock(sitting, setup(), INSTITUTION_WORDS), {
    reason: "Nothing can be scheduled until an exam is ready.",
    fixLabel: "Set up an exam",
    fixHref: "/authoring/exams/new",
  });
  assert.equal(stepBlock(sitting, setup({ ready_to_run: true }), INSTITUTION_WORDS), null);
  const exam = assistantSteps(setup(), INSTITUTION_WORDS)[0];
  assert.ok(exam);
  assert.equal(stepBlock(exam, setup(), INSTITUTION_WORDS), null);
});

test("needs-your-attention lists outcomes to write and results to release, oldest first", () => {
  const row = (over: Partial<ResultsIndexRow>): ResultsIndexRow =>
    ({ sitting_id: "s", name: "Sitting", candidates: 3, draft: 0, not_decided: 0, released: 0, signed_off: 0, mode: "exam", status: "completed", scheduled_for: null, ...over }) as ResultsIndexRow;
  const items = attentionFromResults(
    [row({ sitting_id: "new", name: "Year 4 mock", signed_off: 2 }), row({ sitting_id: "old", name: "February", not_decided: 2, draft: 1 })],
    INSTITUTION_WORDS,
  );
  assert.deepEqual(
    items.map((item) => [item.tag, item.title, item.href]),
    [
      ["3 decisions", "Record outcomes for February", "/sittings/old/results"],
      ["2 ready", "Release results for Year 4 mock", "/sittings/new/results"],
    ],
  );
});

test("a scheduled or training sitting has no decisions waiting", () => {
  const row = (over: Partial<ResultsIndexRow>): ResultsIndexRow =>
    ({ sitting_id: "s", name: "Sitting", candidates: 20, draft: 0, not_decided: 20, released: 0, signed_off: 0, mode: "exam", status: "scheduled", scheduled_for: null, ...over }) as ResultsIndexRow;
  assert.deepEqual(attentionFromResults([row({}), row({ status: "completed", mode: "training" })], INSTITUTION_WORDS), []);
});

test("hire words the decision row as the board does", () => {
  const items = attentionFromResults(
    [{ sitting_id: "a", name: "Band 6 day", candidates: 4, draft: 1, not_decided: 3, released: 0, signed_off: 0, mode: "exam", status: "completed", scheduled_for: null } as ResultsIndexRow],
    EMPLOYER_WORDS,
  );
  assert.deepEqual(items.map((item) => [item.title, item.tag]), [["4 candidates need a hiring decision", "Decide"]]);
});

test("a consultation with no attempt behind it is a station nobody is recording", () => {
  assert.equal(recordingMissing(circuit({ circuit_id: "a" })), false);
  assert.equal(recordingMissing(circuit({ circuit_id: "a", attempt_id: null })), true);
  assert.equal(
    recordingMissing(circuit({ circuit_id: "a", attempt_status: "failed" })),
    true,
  );
  // Reading time has no recording yet and is not a problem.
  assert.equal(
    recordingMissing(circuit({ circuit_id: "a", phase: "reading", attempt_id: null })),
    false,
  );
});

test("the board puts trouble first, then whoever runs out of time soonest", () => {
  const calm = circuit({ circuit_id: "calm", remaining_seconds: 30 });
  const alerting = circuit({ circuit_id: "alerting", alerts: ["clock_overdue"], remaining_seconds: 900 });
  const soon = circuit({ circuit_id: "soon", remaining_seconds: 60 });
  assert.deepEqual(
    boardOrder([calm, alerting, soon]).map((each) => each.circuit_id),
    ["alerting", "calm", "soon"],
  );
});

test("a paused circuit says so rather than naming its phase", () => {
  assert.equal(circuitStatus(circuit({ circuit_id: "a", paused: true })), "Paused");
  assert.equal(circuitStatus(circuit({ circuit_id: "a", phase: "break" })), "Between stations");
  assert.equal(circuitStatus(circuit({ circuit_id: "a", phase: "reading" })), "Reading time");
});

test("a training circuit names the first people and counts the rest", () => {
  const people = (n: number) =>
    Array.from({ length: n }, (_, i) => ({ user_id: `u${i}`, name: `Person ${i}`, email: null }));
  assert.equal(candidatesLabel(circuit({ circuit_id: "a" })), "Nobody on this circuit");
  assert.equal(candidatesLabel(circuit({ circuit_id: "a", candidates: people(2) })), "Person 0 and Person 1");
  assert.equal(
    candidatesLabel(circuit({ circuit_id: "a", candidates: people(5) })),
    "Person 0, Person 1 and 3 more",
  );
});

test("finished runs are headed by the day they ended, newest first", () => {
  const now = new Date(2026, 8, 29, 15, 0);
  const run = (id: string, ended: Date) => ({ id, ended_at: ended.toISOString() });
  const groups = runsByDay(
    [
      run("afternoon", new Date(2026, 8, 29, 14, 0)),
      run("morning", new Date(2026, 8, 29, 9, 0)),
      run("yesterday", new Date(2026, 8, 28, 16, 0)),
      run("last week", new Date(2026, 8, 22, 11, 0)),
    ],
    now,
  );
  assert.deepEqual(
    groups.map((group) => [group.label, group.runs.map((item) => item.id)]),
    [
      ["Today", ["afternoon", "morning"]],
      ["Yesterday", ["yesterday"]],
      ["Tuesday 22 September", ["last week"]],
    ],
  );
});

test("the Today sentence counts what runs and what needs you", () => {
  assert.equal(todaySentence(1, 5), "One circuit is running and five things need you.");
  assert.equal(todaySentence(0, 1), "No circuit is running and one thing needs you.");
  assert.equal(todaySentence(2, 0), "Two circuits are running and nothing needs you.");
});

test("runningLine reads as the Today board does, in each arm's words", () => {
  const circuit = {
    stations_total: 8,
    stations_completed: 3,
    current_station: { slot_id: "s", slot_index: 3 },
    supervisor: { name: "Dr Patel" },
    candidates: Array.from({ length: 8 }, () => ({ name: "A" })),
  } as unknown as LiveCircuit;
  assert.equal(runningLine(circuit, INSTITUTION_WORDS), "Station 4 of 8 · Supervisor: Dr Patel · 8 trainees");
  const three = { ...circuit, candidates: [{}, {}, {}] } as unknown as LiveCircuit;
  assert.equal(runningLine(three, EMPLOYER_WORDS), "3 candidates on stations · Assessor: Dr Patel");
});

test("stillToReviewLine and circuitsBySitting use the board's phrases", () => {
  assert.equal(stillToReviewLine(5, 8, INSTITUTION_WORDS), "5 of 8 trainees still to review");
  const rows = [
    { sitting_id: "a", sitting_name: "Year 3 practice round", circuit_name: "Circuit B" },
    { sitting_id: "b", sitting_name: "Final-year OSCE, summer finals", circuit_name: "A" },
    { sitting_id: "b", sitting_name: "Final-year OSCE, summer finals", circuit_name: "B" },
  ];
  assert.deepEqual(
    circuitsBySitting(rows).map((g) => g.title),
    ["Year 3 practice round · Circuit B", "Final-year OSCE, summer finals · 2 circuits"],
  );
});

test("dateEyebrow and dateTile", () => {
  assert.equal(dateEyebrow(new Date(2026, 10, 5)), "Thursday 5 November");
  assert.deepEqual(dateTile(new Date(2026, 10, 12, 9).toISOString()), { month: "NOV", day: "12" });
});
