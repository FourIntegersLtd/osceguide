import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { circuitReviewSteps, nextReviewAction, stationsToMark, type ReviewStation } from "@/domains/assess/sessions/circuitReviewSteps";

const st = (position: number, state: ReviewStation["state"]): ReviewStation => ({
  slotId: `s${position}`,
  attemptId: null,
  position,
  title: `Station ${position}`,
  state,
});
const four = [st(1, "marked"), st(2, "marked"), st(3, "marked"), st(4, "marked"), st(5, "unmarked"), st(6, "unmarked")];

describe("circuit review steps", () => {
  it("says what is left and that nothing is published", () => {
    const { steps, line } = circuitReviewSteps(four, false);
    assert.equal(steps[0]?.note, "4 of 6 marked");
    assert.equal(steps[1]?.note, "Not sent yet");
    assert.equal(steps[2]?.note, "An admin shares the results");
    assert.equal(line, "Mark the 2 stations left. Then send feedback.");
  });
  it("does not claim stations are marked when nobody sat any", () => {
    const { line } = circuitReviewSteps([st(1, "not_sat"), st(2, "not_sat")], false);
    assert.equal(line, "No one took part in this circuit, so there is nothing to mark.");
  });
  it("lists unmarked stations first", () => {
    assert.deepEqual(stationsToMark(four).map((s) => s.position), [5, 6, 1, 2, 3, 4]);
  });
  it("leaves out stations nobody sat", () => {
    assert.equal(stationsToMark([st(1, "not_sat")]).length, 0);
  });
});

describe("the next thing to do once a circuit has ended", () => {
  it("is to mark the first unmarked station", () => {
    const next = nextReviewAction([st(1, "marked"), st(2, "unmarked"), st(3, "unmarked")], false);
    assert.deepEqual(next, { kind: "mark", label: "Mark next station", station: st(2, "unmarked") });
  });
  it("is to publish once everything sat is marked, and a not-sat station does not hold it up", () => {
    assert.deepEqual(nextReviewAction([st(1, "marked"), st(2, "not_sat")], false), { kind: "publish", label: "Send feedback" });
  });
  it("is the results once published", () => {
    assert.deepEqual(nextReviewAction([st(1, "marked")], true), { kind: "results", label: "Open results" });
  });
  it("is the results when nobody sat, since there is nothing to mark or share", () => {
    assert.deepEqual(nextReviewAction([st(1, "not_sat")], false), { kind: "results", label: "Open results" });
  });
});
