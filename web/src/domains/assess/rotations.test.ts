import assert from "node:assert/strict";
import test from "node:test";
import { assessorTally, proposeRotations } from "@/domains/assess/rotations";

test("candidates are spread over the chosen assessors in turn", () => {
  assert.deepEqual(proposeRotations(["c1", "c2", "c3", "c4", "c5"], ["a1", "a2"]), {
    c1: "a1",
    c2: "a2",
    c3: "a1",
    c4: "a2",
    c5: "a1",
  });
});

test("with no assessor chosen nobody is assigned", () => {
  assert.deepEqual(proposeRotations(["c1", "c2"], []), {});
});

test("one assessor takes every candidate", () => {
  assert.deepEqual(proposeRotations(["c1", "c2"], ["a1"]), { c1: "a1", c2: "a1" });
});

test("the tally counts candidates per assessor, in the assessor order, and the unassigned", () => {
  const tally = assessorTally(["c1", "c2", "c3"], { c1: "a1", c2: "a2" }, { a1: "Dan Lowe", a2: "Sara Khan" });
  assert.deepEqual(tally.perAssessor, [
    { id: "a1", name: "Dan Lowe", count: 1 },
    { id: "a2", name: "Sara Khan", count: 1 },
  ]);
  assert.equal(tally.unassigned, 1);
});

test("a stale assignment for someone no longer sitting is not counted", () => {
  const tally = assessorTally(["c1"], { c1: "a1", gone: "a1" }, { a1: "Dan Lowe" });
  assert.deepEqual(tally.perAssessor, [{ id: "a1", name: "Dan Lowe", count: 1 }]);
  assert.equal(tally.unassigned, 0);
});
