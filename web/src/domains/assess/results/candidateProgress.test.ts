import assert from "node:assert/strict";
import { test } from "node:test";
import { candidateProgress, candidateStage } from "./candidateProgress";

const marked = { marked: true, overall_rag: 1 };
const awaiting = { marked: true, overall_rag: null };

test("a marked candidate whose reviews are outstanding", () => {
  const candidate = { stations: [marked, awaiting], decision: null };
  assert.deepEqual(
    candidateProgress(candidate).map((step) => [step.id, step.state, step.note]),
    [
      ["marked", "done", "2 of 2 marked"],
      ["reviewed", "todo", "1 of 2 reviewed"],
      ["decided", "todo", "Not decided"],
      ["signed_off", "todo", "Not signed off"],
      ["released", "todo", "Not released"],
    ],
  );
  assert.equal(candidateStage(candidate), "Marked");
});

test("signing off before reviews are complete is allowed but flagged", () => {
  const candidate = {
    stations: [marked, awaiting],
    decision: { assessment_outcome: "pass", signed_off_at: "t", released_at: null },
  };
  const steps = candidateProgress(candidate);
  assert.deepEqual([steps[1]?.state, steps[1]?.note], ["attention", "Reviews not complete"]);
  assert.deepEqual([steps[2]?.note, steps[3]?.state], ["Pass", "done"]);
  assert.equal(candidateStage(candidate), "Signed off");
});

test("a released result is complete, and nobody sat is not marked", () => {
  const released = {
    stations: [marked],
    decision: { assessment_outcome: "fail", signed_off_at: "t", released_at: "t2" },
  };
  assert.deepEqual(candidateProgress(released).map((step) => step.state), ["done", "done", "done", "done", "done"]);
  assert.equal(candidateStage(released), "Released");
  assert.equal(candidateStage({ stations: [], decision: null }), "Not marked");
});
