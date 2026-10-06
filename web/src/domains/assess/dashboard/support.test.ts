import assert from "node:assert/strict";
import test from "node:test";
import type { LiveCircuit, OrgSetup } from "@/domains/assess/dashboard/api";
import {
  runsByDay,
  boardOrder,
  candidatesLabel,
  circuitStatus,
  nextSetupAction,
  recordingMissing,
  setupSteps,
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

test("a fresh organisation sees the eight steps in build order, all to do", () => {
  assert.deepEqual(
    setupSteps(setup()).map((step) => [step.id, step.label, step.state, step.note, step.path]),
    [
      ["rubric", "Marking scheme", "todo", "Publish one", "/authoring/rubrics"],
      ["exam", "Exam", "todo", "Publish one", "/authoring/exams"],
      ["programme", "Programme", "todo", "Add one", "/programmes"],
      ["template", "Station template", "todo", "Publish one", "/authoring/station-templates"],
      ["stations", "Stations", "todo", "None to run", "/authoring/stations"],
      ["team", "Team", "todo", "Invite a supervisor", "/team"],
      ["trainees", "Trainees", "todo", "None added", "/trainees"],
      ["sitting", "First sitting", "todo", "Not scheduled", "/sittings/new"],
    ],
  );
});

test("the one action is the first step not done, in order", () => {
  assert.deepEqual(nextSetupAction(setup()), {
    step: "rubric",
    path: "/authoring/rubrics",
    label: "Write a marking scheme",
    line: "Start with a marking scheme: what candidates are marked against.",
  });
  assert.equal(nextSetupAction(setup({ rubric_published: true }))?.step, "exam");
  // Done out of order, the earliest gap still leads.
  assert.equal(nextSetupAction(setup({ rubric_published: true, exam_published: true, team_invited: true }))?.step, "programme");
});

test("nothing is left to do once every step is done", () => {
  const all = setup({
    rubric_published: true,
    exam_published: true,
    programme_exam_rubric_ready: true,
    template_published: true,
    stations_available: true,
    team_invited: true,
    trainees_added: true,
    sitting_scheduled: true,
  });
  assert.equal(nextSetupAction(all), null);
  assert.equal(setupSteps(all).every((step) => step.state === "done" && step.note === "Done"), true);
});

test("the station step follows what is available, not what was authored", () => {
  // An institution that adopted the platform catalogue can examine somebody
  // today, so telling it to author a station was a step it had already taken.
  const done = setupSteps(setup({ stations_available: true })).find((step) => step.id === "stations");
  const not = setupSteps(setup()).find((step) => step.id === "stations");
  assert.equal(done?.state, "done");
  assert.equal(not?.state, "todo");
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
