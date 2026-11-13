import assert from "node:assert/strict";
import { test } from "node:test";
import { cueEvents, liveState } from "./cues";
import type { Sample } from "./sampler";

const s = (over: Partial<Sample> = {}): Sample => ({
  at_ms: 0,
  face: true,
  away: false,
  yaw: 0,
  pitch: 0,
  smile: 0,
  nod: false,
  ...over,
});
const many = (n: number, over: Partial<Sample> = {}): Sample[] =>
  Array.from({ length: n }, (_, i) => s({ at_ms: i * 1000, ...over }));

test("fewer than 3 samples is neutral: Getting ready", () => {
  assert.deepEqual(liveState(many(2)), { tone: "neutral", text: "Getting ready" });
});

test("last 3 samples without a face is a warning", () => {
  assert.deepEqual(liveState([...many(4), ...many(3, { face: false })]), {
    tone: "warning",
    text: "Move into view of the camera",
  });
});

test("6 or more away samples in a row is a warning with the count", () => {
  assert.deepEqual(liveState([...many(2), ...many(7, { away: true })]), {
    tone: "warning",
    text: "Looking away for 7 seconds",
  });
});

test("5 away samples is still facing the patient", () => {
  assert.deepEqual(liveState([...many(2), ...many(5, { away: true })]), {
    tone: "success",
    text: "Facing the patient",
  });
});

test("otherwise facing the patient", () => {
  assert.deepEqual(liveState(many(5)), { tone: "success", text: "Facing the patient" });
});

test("a nod gives a Nodded event", () => {
  const samples = [...many(3), s({ at_ms: 3000, nod: true })];
  assert.deepEqual(cueEvents(samples), [{ at_ms: 3000, kind: "nod", text: "Nodded" }]);
});

test("smile crossing 50 after 5 seconds below gives Smiled, once", () => {
  const samples = [...many(5, { smile: 10 }), s({ at_ms: 5000, smile: 70 }), s({ at_ms: 6000, smile: 80 })];
  assert.deepEqual(cueEvents(samples), [{ at_ms: 5000, kind: "smile", text: "Smiled" }]);
});

test("smile crossing after fewer than 5 seconds below gives nothing", () => {
  const samples = [...many(3, { smile: 10 }), s({ at_ms: 3000, smile: 70 })];
  assert.deepEqual(cueEvents(samples), []);
});

test("an away run of 6 that ends gives Looked back with its length", () => {
  const samples = [...many(2), ...many(6, { away: true }).map((x, i) => ({ ...x, at_ms: 2000 + i * 1000 })), s({ at_ms: 8000 })];
  assert.deepEqual(cueEvents(samples), [{ at_ms: 8000, kind: "attention", text: "Looked back after 6 seconds" }]);
});

test("an away run of 5 that ends gives nothing", () => {
  const samples = [...many(2), ...many(5, { away: true }), s({ at_ms: 9000 })];
  assert.deepEqual(cueEvents(samples), []);
});

test("events are newest first and capped at 8", () => {
  const samples = many(12).map((x, i) => ({ ...x, at_ms: i * 1000, nod: true }));
  const events = cueEvents(samples);
  assert.equal(events.length, 8);
  assert.equal(events[0]?.at_ms, 11000);
});
