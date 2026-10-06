import assert from "node:assert/strict";
import { test } from "node:test";
import { countsFromReport, sittingNext, sittingSteps, type SittingStepsInput } from "./sittingSteps";

const can = { schedule: true, signOff: true };
const ended = { started_at: "t", ended_at: "t2" };

test("a new sitting is waiting for a date", () => {
  const input: SittingStepsInput = { scheduledFor: null, circuits: [], counts: null, can };
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
    line: "Set a date for this sitting.",
    actionable: true,
    waiting: 0,
  });
});

test("only people who may schedule are offered the action", () => {
  const next = sittingNext({ scheduledFor: "d", circuits: [], counts: null, can: { schedule: false, signOff: true } });
  assert.deepEqual([next.id, next.actionable], ["circuits", false]);
});

test("a running circuit is the open step", () => {
  const input: SittingStepsInput = {
    scheduledFor: "d",
    circuits: [ended, { started_at: "t", ended_at: null }],
    counts: null,
    can,
  };
  assert.equal(sittingSteps(input)[2]?.note, "1 of 2 finished");
  assert.deepEqual(sittingNext(input), { id: "run", line: "A circuit is running.", actionable: false, waiting: 0 });
});

test("signed-off results waiting are the release action", () => {
  const input: SittingStepsInput = {
    scheduledFor: "d",
    circuits: [ended],
    counts: { candidates: 3, stations: 6, stationsSat: 1, stationsMarked: 6, decided: 3, signedOff: 2, released: 0 },
    can,
  };
  assert.deepEqual(
    sittingSteps(input).map((step) => step.state),
    ["done", "done", "done", "done", "done", "todo"],
  );
  assert.deepEqual(sittingNext(input), {
    id: "release",
    line: "2 results signed off and not yet released.",
    actionable: true,
    waiting: 2,
  });
});

test("everything released is done", () => {
  const next = sittingNext({
    scheduledFor: "d",
    circuits: [ended],
    counts: { candidates: 1, stations: 2, stationsSat: 1, stationsMarked: 2, decided: 1, signedOff: 1, released: 1 },
    can,
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
    can,
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
    can,
  };
  assert.deepEqual([sittingSteps(input)[2]?.state, sittingSteps(input)[2]?.note], ["attention", "Circuit ended, nobody sat"]);
  assert.equal(sittingNext(input).id, "run");
});

test("the results page judges Run by stations sat", () => {
  const counts = { candidates: 1, stations: 2, stationsSat: 0, stationsMarked: 0, decided: 0, signedOff: 0, released: 0 };
  const idle = sittingSteps({ scheduledFor: "d", circuits: null, counts, can });
  assert.deepEqual([idle[1]?.note, idle[2]?.state, idle[2]?.note], ["1 candidate assigned", "todo", "Nobody has sat yet"]);
  const half = sittingSteps({ scheduledFor: "d", circuits: null, counts: { ...counts, stationsSat: 1 }, can });
  assert.equal(half[2]?.note, "1 of 2 stations sat");
});
