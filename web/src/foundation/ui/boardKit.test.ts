import assert from "node:assert/strict";
import { test } from "node:test";
import { boardSegChoice } from "./boardKit";

test("the chosen rating takes the colour of its place in the scale, the others stay white", () => {
  assert.match(boardSegChoice(true, "success"), /bg-osce-success-bg text-osce-success-text/);
  assert.match(boardSegChoice(true, "warning"), /bg-osce-warning-bg/);
  assert.match(boardSegChoice(true, "danger"), /bg-osce-danger-bg/);
  assert.match(boardSegChoice(true, "neutral"), /bg-osce-navActive/);
  assert.match(boardSegChoice(false, "success"), /bg-osce-surface/);
  assert.doesNotMatch(boardSegChoice(false, "success"), /success/);
});
