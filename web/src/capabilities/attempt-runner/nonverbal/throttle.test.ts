import assert from "node:assert/strict";
import { test } from "node:test";
import { FrameThrottle } from "./throttle";

test("frames closer than 250 ms are skipped", () => {
  const t = new FrameThrottle();
  assert.equal(t.shouldProcess(1000), true);
  assert.equal(t.shouldProcess(1200), false);
  assert.equal(t.shouldProcess(1250), true);
});

test("a slow detector (mean over 20 frames above 60 ms) widens the gap to 500 ms", () => {
  const t = new FrameThrottle();
  for (let i = 0; i < 20; i++) t.record(80);
  assert.equal(t.intervalMs, 500);
  t.shouldProcess(0);
  assert.equal(t.shouldProcess(300), false);
  assert.equal(t.shouldProcess(500), true);
});

test("a fast detector keeps 250 ms", () => {
  const t = new FrameThrottle();
  for (let i = 0; i < 20; i++) t.record(20);
  assert.equal(t.intervalMs, 250);
});
