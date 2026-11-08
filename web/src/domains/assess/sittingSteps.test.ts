import assert from "node:assert/strict";
import { test } from "node:test";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import { circuitToOpen, countsFromReport, sittingNext, sittingSteps, type SittingStepsInput } from "./sittingSteps";

const can = { schedule: true, signOff: true };
const ended = { started_at: "t", ended_at: "t2" };

test("a new sitting is waiting for a date", () => {
  const input: SittingStepsInput = { scheduledFor: null, circuits: [], counts: null, training: false, can, words: INSTITUTION_WORDS };
  assert.deepEqual(
    sittingSteps(input).map((step) => [step.id, step.state, step.note]),
    [
      ["schedule", "todo", "No date"],
      ["circuits", "todo", "None yet"],
      ["run", "todo", "Not started"],
      ["mark", "todo", "Not started"],
      ["decide", "todo", "Not started"],
      ["release", "todo", "Not started"],
    ],
  );
  assert.deepEqual(sittingNext(input), {
    id: "schedule",
    line: "Set a date so candidates know when to come.",
    hero: null,
    actionable: true,
    waiting: 0,
  });
});

test("only people who may schedule are offered the action", () => {
  const next = sittingNext({ scheduledFor: "d", circuits: [], counts: null, training: false, can: { schedule: false, signOff: true }, words: INSTITUTION_WORDS });
  assert.deepEqual([next.id, next.actionable], ["circuits", false]);
});

test("a running circuit is the open step", () => {
  const input: SittingStepsInput = {
    scheduledFor: "d",
    circuits: [ended, { started_at: "t", ended_at: null }],
    counts: null,
    training: false,
    can,
    words: INSTITUTION_WORDS,
  };
  assert.equal(sittingSteps(input)[2]?.note, "1 of 2 finished");
  assert.deepEqual(sittingNext(input), {
    id: "run",
    line: "A circuit is running. Follow it from its console.",
    hero: null,
    actionable: true,
    waiting: 0,
  });
});

test("signed-off results waiting are the release action", () => {
  const input: SittingStepsInput = {
    scheduledFor: "d",
    circuits: [ended],
    counts: { candidates: 3, stations: 6, stationsSat: 1, stationsMarked: 6, decided: 3, signedOff: 2, released: 0 },
    training: false,
    can,
    words: INSTITUTION_WORDS,
  };
  assert.deepEqual(
    sittingSteps(input).map((step) => step.state),
    ["done", "done", "done", "done", "done", "todo"],
  );
  assert.deepEqual(sittingNext(input), {
    id: "release",
    line: "2 results signed off and not yet released.",
    hero: null,
    actionable: true,
    waiting: 2,
  });
});

test("everything released is done", () => {
  const next = sittingNext({
    scheduledFor: "d",
    circuits: [ended],
    counts: { candidates: 1, stations: 2, stationsSat: 1, stationsMarked: 2, decided: 1, signedOff: 1, released: 1 },
    training: false,
    can,
    words: INSTITUTION_WORDS,
  });
  assert.deepEqual([next.id, next.actionable], ["done", false]);
});

test("counts are read off the report", () => {
  assert.deepEqual(
    countsFromReport({
      totals: { candidates: 2, stations: 4, stations_marked: 3, decisions_released: 0 },
      candidates: [
        { decision: { assessment_outcome: "pass", signed_off_at: "x" } },
        { decision: null },
      ],
    }),
    { candidates: 2, stations: 4, stationsSat: 0, stationsMarked: 3, decided: 1, signedOff: 1, released: 0 },
  );
});

test("the results page has no circuits, so every station sat in the report shows Run done", () => {
  const steps = sittingSteps({
    scheduledFor: "d",
    circuits: null,
    counts: { candidates: 1, stations: 2, stationsSat: 2, stationsMarked: 1, decided: 0, signedOff: 0, released: 0 },
    training: false,
    can,
    words: INSTITUTION_WORDS,
  });
  assert.deepEqual(
    steps.map((step) => [step.id, step.state]),
    [["schedule", "done"], ["circuits", "done"], ["run", "done"], ["mark", "todo"], ["decide", "todo"], ["release", "todo"]],
  );
});

test("an ended circuit nobody sat is attention, not finished", () => {
  const input: SittingStepsInput = {
    scheduledFor: "d",
    circuits: [ended],
    counts: { candidates: 1, stations: 1, stationsSat: 0, stationsMarked: 0, decided: 0, signedOff: 0, released: 0 },
    training: false,
    can,
    words: INSTITUTION_WORDS,
  };
  assert.deepEqual([sittingSteps(input)[2]?.state, sittingSteps(input)[2]?.note], ["attention", "Circuit ended, nobody sat"]);
  assert.equal(sittingNext(input).id, "run");
});

test("the results page judges Run by stations sat", () => {
  const counts = { candidates: 1, stations: 2, stationsSat: 0, stationsMarked: 0, decided: 0, signedOff: 0, released: 0 };
  const idle = sittingSteps({ scheduledFor: "d", circuits: null, counts, training: false, can, words: INSTITUTION_WORDS });
  assert.deepEqual([idle[1]?.note, idle[2]?.state, idle[2]?.note], ["1 candidate assigned", "todo", "Nobody has sat yet"]);
  const half = sittingSteps({ scheduledFor: "d", circuits: null, counts: { ...counts, stationsSat: 1 }, training: false, can, words: INSTITUTION_WORDS });
  assert.equal(half[2]?.note, "1 of 2 stations sat");
});

// R-22: a supervisor (no sign_off_results) was told "Marking is not finished" forever,
// Run had no link and said "start a new circuit", and training showed Decide and Release.
test("a supervisor past marking is told an administrator decides, not that marking is unfinished", () => {
  const marked = { candidates: 2, stations: 4, stationsSat: 4, stationsMarked: 4, decided: 0, signedOff: 0, released: 0 };
  const input: SittingStepsInput = {
    scheduledFor: "d",
    circuits: [ended],
    counts: marked,
    training: false,
    can: { schedule: false, signOff: false },
    words: INSTITUTION_WORDS,
  };
  assert.deepEqual(sittingNext(input), {
    id: "decide",
    line: "Waiting for an administrator to record and sign off each outcome.",
    hero: null,
    actionable: false,
    waiting: 0,
  });
  assert.equal(
    sittingNext({ ...input, counts: { ...marked, decided: 2, signedOff: 2 } }).line,
    "2 results signed off, waiting for an administrator to release them.",
  );
});

test("the Run step opens the circuit's console and never says start a new circuit", () => {
  const input: SittingStepsInput = {
    scheduledFor: "d",
    circuits: [ended],
    counts: { candidates: 1, stations: 1, stationsSat: 0, stationsMarked: 0, decided: 0, signedOff: 0, released: 0 },
    training: false,
    can,
    words: INSTITUTION_WORDS,
  };
  const next = sittingNext(input);
  assert.deepEqual([next.id, next.actionable], ["run", true]);
  assert.equal(next.line, "The circuit ended and nobody sat. Open it to see what happened, or add another circuit.");
  const waiting = { id: "w", started_at: null, ended_at: null };
  const live = { id: "l", started_at: "t", ended_at: null };
  assert.equal(circuitToOpen([{ ...ended, id: "e" }, waiting, live])?.id, "l");
  assert.equal(circuitToOpen([{ ...ended, id: "e" }, waiting])?.id, "w");
  assert.equal(circuitToOpen([{ ...ended, id: "e" }])?.id, "e");
});

test("a training sitting stops at Mark: no Decide or Release", () => {
  const input: SittingStepsInput = {
    scheduledFor: "d",
    circuits: [ended],
    counts: { candidates: 1, stations: 2, stationsSat: 2, stationsMarked: 2, decided: 0, signedOff: 1, released: 0 },
    training: true,
    can,
    words: INSTITUTION_WORDS,
  };
  assert.deepEqual(
    sittingSteps(input).map((step) => step.id),
    ["schedule", "circuits", "run", "mark"],
  );
  assert.deepEqual(sittingNext(input), { id: "done", line: "Every station has been marked.", actionable: false, waiting: 1, hero: null });
});

test("a scheduled sitting with circuits says how many candidates are assigned, not how many circuits", () => {
  const counts = { candidates: 8, stations: 0, stationsSat: 0, stationsMarked: 0, decided: 0, signedOff: 0, released: 0 };
  const circuit = { started_at: null, ended_at: null };
  const steps = sittingSteps({ scheduledFor: "d", circuits: [circuit, circuit], counts, training: false, can, words: INSTITUTION_WORDS });
  assert.equal(steps[1]?.note, "8 candidates assigned");
  assert.equal(
    sittingSteps({ scheduledFor: "d", circuits: [circuit, circuit], counts: null, training: false, can, words: INSTITUTION_WORDS })[1]?.note,
    "2 circuits",
  );
});

const circuit = (over: object) => ({ id: "c", started_at: null, ended_at: null, supervisor_user_id: "u", trainee_count: 1, ...over });
const hireCounts = { candidates: 8, stations: 5, stationsSat: 0, stationsMarked: 0, decided: 0, signedOff: 0, released: 0 };
const hireBase = { scheduledFor: new Date(2026, 10, 20, 9).toISOString(), counts: hireCounts, training: false, can, words: EMPLOYER_WORDS };

test("the hire hero counts finished rotations while running, and keeps the live board as its target", () => {
  const running = sittingNext({
    ...hireBase,
    circuits: [circuit({ started_at: "a", ended_at: "b" }), circuit({ started_at: "a" }), circuit({}), circuit({})],
  });
  assert.deepEqual(running.hero, { title: "1 of 4 rotations finished", label: "Watch it", target: { kind: "live" } });
  assert.equal(running.line, "1 running, 2 waiting.");
});

test("the hire hero names the day when ahead, today on the day, and the date beyond a week", () => {
  const title = (now: Date, scheduledFor = hireBase.scheduledFor) =>
    sittingNext({ ...hireBase, scheduledFor, circuits: [circuit({})], now }).hero?.title;
  assert.equal(title(new Date(2026, 10, 18, 9)), "Ready for Friday");
  assert.equal(title(new Date(2026, 10, 20, 8)), "Ready for today");
  assert.equal(title(new Date(2026, 10, 21)), "Ready to go");
  assert.equal(title(new Date(2026, 10, 1, 9)), "Ready for 20 November");
});

test("no assessor sends the hero to that rotation's edit page, and only an unstarted one counts", () => {
  const lacking = circuit({ id: "lacking", supervisor_user_id: null });
  const hero = sittingNext({ ...hireBase, circuits: [circuit({ id: "ok" }), lacking] }).hero;
  assert.deepEqual(hero, { title: "A station has no assessor", label: "Choose an assessor", target: { kind: "edit", circuitId: "lacking" } });
  const live = sittingNext({ ...hireBase, circuits: [circuit({ id: "r", supervisor_user_id: null, started_at: "a" })] }).hero;
  assert.equal(live?.label, "Watch it");
});

test("choosing an assessor is actionable only for someone who may schedule, whether or not there are circuits to open", () => {
  const lacking = circuit({ id: "lacking", supervisor_user_id: null });
  assert.equal(sittingNext({ ...hireBase, circuits: [lacking] }).actionable, true);
  assert.equal(sittingNext({ ...hireBase, can: { schedule: false, signOff: true }, circuits: [lacking] }).actionable, false);
});

test("a live rotation outranks a later one with no assessor", () => {
  const next = sittingNext({
    ...hireBase,
    circuits: [circuit({ id: "live", started_at: "a" }), circuit({ id: "lacking", supervisor_user_id: null })],
  });
  assert.deepEqual(next.hero, { title: "0 of 2 rotations finished", label: "Watch it", target: { kind: "live" } });
  assert.equal(next.line, "1 running, 1 waiting.");
});
