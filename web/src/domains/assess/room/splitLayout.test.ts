import assert from "node:assert/strict";
import test from "node:test";
import { SPLIT, clampWidth, loadSplit, saveSplit, stepWidth } from "@/domains/assess/room/splitLayout";

test("the panel stays between its limits and leaves the tiles their minimum", () => {
  assert.equal(clampWidth(100), SPLIT.min);
  assert.equal(clampWidth(900), SPLIT.max);
  assert.equal(clampWidth(500, 800), 440);
  assert.equal(clampWidth(Number.NaN), SPLIT.initial);
});

test("left widens, right narrows, shift steps further, other keys do nothing", () => {
  assert.equal(stepWidth(380, "ArrowLeft", false), 396);
  assert.equal(stepWidth(380, "ArrowRight", true), 316);
  assert.equal(stepWidth(380, "Tab", false), 380);
  assert.equal(stepWidth(550, "ArrowLeft", true), SPLIT.max);
});

test("width and collapsed round-trip, a stored width is re-clamped, broken storage gives the default", () => {
  const data = new Map<string, string>();
  const store = { getItem: (k: string) => data.get(k) ?? null, setItem: (k: string, v: string) => void data.set(k, v) };
  saveSplit({ width: 450, collapsed: true }, store);
  assert.deepEqual(loadSplit(store), { width: 450, collapsed: true });
  data.set(SPLIT.storageKey, JSON.stringify({ width: 5000 }));
  assert.deepEqual(loadSplit(store), { width: SPLIT.max, collapsed: false });
  const broken = { getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } };
  assert.deepEqual(loadSplit(broken), { width: SPLIT.initial, collapsed: false });
  saveSplit({ width: 400, collapsed: false }, broken);
});
