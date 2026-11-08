import assert from "node:assert/strict";
import test from "node:test";
import { assessorTally, proposeRotations, reconcileRotations } from "@/domains/assess/rotations";

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

test("ticking another assessor keeps a hand-set candidate and deals the rest, evenly", () => {
  const ids = ["c1", "c2", "c3", "c4"];
  const dealt = proposeRotations(ids, ["a1"]);
  // c2 was changed by hand to a1 -> still a1 (unchanged from dealt), c3 was set by hand to a2.
  const current = { ...dealt, c3: "a2" };
  const next = reconcileRotations(ids, current, dealt, ["a1", "a2"]);
  assert.equal(next.c3, "a2", "the hand-set candidate stays");
  assert.deepEqual(assessorTally(ids, next, { a1: "A", a2: "B" }).perAssessor.map((r) => r.count), [2, 2]);
});

test("unticking an assessor never leaves a candidate on them and keeps hand-set ones", () => {
  const ids = ["c1", "c2", "c3", "c4"];
  const dealt = { c1: "a1", c2: "a2", c3: "a3", c4: "a1" };
  const current = { ...dealt, c2: "a1" };
  const next = reconcileRotations(ids, current, dealt, ["a1", "a2"]);
  assert.equal(next.c2, "a1", "set by hand to a1, still ticked");
  assert.ok(Object.values(next).every((a) => a === "a1" || a === "a2"));
  assert.deepEqual(assessorTally(ids, next, { a1: "A", a2: "B" }).perAssessor.map((r) => r.count), [2, 2]);
});

test("with nobody ticked nobody is assigned", () => {
  assert.deepEqual(reconcileRotations(["c1"], { c1: "a1" }, { c1: "a1" }, []), {});
});
