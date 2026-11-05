import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { circuitReviewSteps, stationsToMark, type ReviewStation } from "@/domains/assess/results/circuitReviewSteps";

const st = (position: number, unmarked: boolean, marked: boolean): ReviewStation => ({
  slotId: `s${position}`,
  attemptId: null,
  position,
  title: `Station ${position}`,
  unmarked,
  marked,
});
const four = [st(1, false, true), st(2, false, true), st(3, false, true), st(4, false, true), st(5, true, false), st(6, true, false)];

describe("circuit review steps", () => {
  it("says what is left and that nothing is published", () => {
    const { steps, line } = circuitReviewSteps(four, false);
    assert.equal(steps[0]?.note, "4 of 6 marked");
    assert.equal(steps[1]?.note, "Not published yet");
    assert.equal(steps[2]?.note, "Admin decides and releases");
    assert.equal(line, "Mark the 2 stations left, then share one summary with the candidate.");
  });
  it("lists unmarked stations first", () => {
    assert.deepEqual(stationsToMark(four).map((s) => s.position), [5, 6, 1, 2, 3, 4]);
  });
  it("leaves out stations nobody sat", () => {
    assert.equal(stationsToMark([st(1, false, false)]).length, 0);
  });
});
