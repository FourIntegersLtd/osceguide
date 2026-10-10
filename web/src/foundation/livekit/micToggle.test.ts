import assert from "node:assert/strict";
import { test } from "node:test";
import { micToggle } from "./micToggle";

test("the mic toggle offers the opposite of the current state", () => {
  assert.deepEqual(micToggle(true), { label: "Mute", next: false });
  assert.deepEqual(micToggle(false), { label: "Unmute", next: true });
});

test("the mic toggle can say whose microphone it is", () => {
  assert.deepEqual(micToggle(true, "me"), { label: "Mute me", next: false });
  assert.deepEqual(micToggle(false, "me"), { label: "Unmute me", next: true });
});
