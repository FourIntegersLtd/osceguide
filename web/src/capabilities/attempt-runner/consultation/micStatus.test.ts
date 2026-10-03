import assert from "node:assert/strict";
import { test } from "node:test";
import { micStatus } from "./micStatus";

const speaking = { blocked: false, connected: true, enabled: true, speaking: true, level: 0.4 };

test("a blocked microphone is reported even while the room is reconnecting", () => {
  assert.equal(micStatus({ ...speaking, blocked: true, connected: false }), "Mic blocked");
});

test("before the room connects the mic is still being prepared", () => {
  assert.equal(micStatus({ ...speaking, connected: false }), "Preparing mic…");
});

test("a muted mic says so, and a silent one is ready", () => {
  assert.equal(micStatus({ ...speaking, enabled: false }), "Mic off");
  assert.equal(micStatus({ ...speaking, speaking: false }), "Mic ready");
});

test("the speaking level picks the hint", () => {
  assert.equal(micStatus({ ...speaking, level: 0.01 }), "Speak up a little");
  assert.equal(micStatus({ ...speaking, level: 0.4 }), "Mic hears you");
  assert.equal(micStatus({ ...speaking, level: 0.95 }), "Very loud");
});
