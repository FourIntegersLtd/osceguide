import assert from "node:assert/strict";
import { test } from "node:test";
import { radioFocusTarget } from "@/capabilities/authoring/rubrics/chipRadioKeys";

test("arrows move focus around the chips and wrap, other keys do nothing", () => {
  assert.equal(radioFocusTarget(3, 0, "ArrowRight"), 1);
  assert.equal(radioFocusTarget(3, 2, "ArrowDown"), 0);
  assert.equal(radioFocusTarget(3, 0, "ArrowLeft"), 2);
  assert.equal(radioFocusTarget(3, 1, "ArrowUp"), 0);
  assert.equal(radioFocusTarget(3, 1, " "), null);
  assert.equal(radioFocusTarget(3, 1, "Enter"), null);
  assert.equal(radioFocusTarget(0, 0, "ArrowRight"), null);
});

test("with nothing focused yet, ArrowLeft lands on the last chip and ArrowRight on the second", () => {
  assert.equal(radioFocusTarget(4, -1, "ArrowLeft"), 3);
  assert.equal(radioFocusTarget(4, -1, "ArrowRight"), 1);
});
