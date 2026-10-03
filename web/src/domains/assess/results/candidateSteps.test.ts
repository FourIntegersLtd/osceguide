import assert from "node:assert/strict";
import { test } from "node:test";
import { candidateSteps } from "./candidateSteps";

const candidates = [
  { name: "Amara", stations: [{ slot_id: "a1", attempt_id: "at-a1", station_title: "Chest pain" }] },
  // Never rostered onto this station, so stepping skips them.
  { name: "Ben", stations: [{ slot_id: "b2", attempt_id: null, station_title: "Headache" }] },
  { name: "Chidi", stations: [{ slot_id: "c1", attempt_id: null, station_title: "Chest pain" }] },
];

test("steps between the candidates who took the same station", () => {
  assert.deepEqual(candidateSteps(candidates, "a1"), {
    position: 1,
    total: 2,
    previous: null,
    next: { slotId: "c1", attemptId: null, name: "Chidi" },
  });
  assert.deepEqual(candidateSteps(candidates, "c1")?.previous, {
    slotId: "a1",
    attemptId: "at-a1",
    name: "Amara",
  });
});

test("offers no steps for a slot the report does not hold, or an untitled station", () => {
  assert.equal(candidateSteps(candidates, "zz"), null);
  assert.equal(
    candidateSteps([{ name: "Dee", stations: [{ slot_id: "d1", attempt_id: null, station_title: null }] }], "d1"),
    null,
  );
});
