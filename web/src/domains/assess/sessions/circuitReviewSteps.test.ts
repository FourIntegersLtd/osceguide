import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { circuitReviewSteps, stationsToMark, type ReviewStation } from "@/domains/assess/sessions/circuitReviewSteps";

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
    assert.equal(steps[1]?.note, "Not published yet");
    assert.equal(steps[2]?.note, "Admin decides and releases");
    assert.equal(line, "Mark the 2 stations left, then share one summary with the candidate.");
  });
  it("does not claim stations are marked when nobody sat any", () => {
    const { line } = circuitReviewSteps([st(1, "not_sat"), st(2, "not_sat")], false);
    assert.equal(line, "No one sat this circuit, so there is nothing to mark.");
  });
  it("lists unmarked stations first", () => {
    assert.deepEqual(stationsToMark(four).map((s) => s.position), [5, 6, 1, 2, 3, 4]);
  });
  it("leaves out stations nobody sat", () => {
    assert.equal(stationsToMark([st(1, "not_sat")]).length, 0);
  });
});
