import assert from "node:assert/strict";
import test from "node:test";
import {
  BREAK_MINUTES_BOUNDS,
  DEFAULT_READING_MINUTES,
  MAX_EXAM_STATIONS,
  breakPositions,
  clampBreakMinutes,
  clampBreaks,
  clampReadingMinutes,
  modeSupportsBreaks,
} from "@/domains/assess/timing";

test("a break can only fall between two stations", () => {
  assert.deepEqual(breakPositions(0), []);
  assert.deepEqual(breakPositions(1), []);
  assert.deepEqual(breakPositions(2), [1]);
  assert.deepEqual(breakPositions(4), [1, 2, 3]);
});

test("breaks that stopped fitting are dropped, deduplicated and sorted", () => {
  // A station came off the circuit, so "after 4" now points past the end.
  assert.deepEqual(clampBreaks([4, 2, 2, 9, 0, -1], 4), [2]);
  assert.deepEqual(clampBreaks([3, 1, 2], 4), [1, 2, 3]);
  // One station: there is no gap to put anything in.
  assert.deepEqual(clampBreaks([1, 2], 1), []);
  assert.deepEqual(clampBreaks([1, 2], 0), []);
  assert.deepEqual(clampBreaks([], 5), []);
  assert.deepEqual(clampBreaks([1.5, Number.NaN], 5), []);
});

test("a break length is clamped into the bounds the server uses", () => {
  assert.equal(clampBreakMinutes(0), BREAK_MINUTES_BOUNDS.min);
  assert.equal(clampBreakMinutes(-20), BREAK_MINUTES_BOUNDS.min);
  assert.equal(clampBreakMinutes(999), BREAK_MINUTES_BOUNDS.max);
  assert.equal(clampBreakMinutes(7.4), 7);
  assert.equal(clampBreakMinutes(Number.NaN), 5);
});

test("only an examination has breaks", () => {
  assert.equal(modeSupportsBreaks("exam"), true);
  assert.equal(modeSupportsBreaks("EXAM"), true);
  assert.equal(modeSupportsBreaks("training"), false);
  assert.equal(modeSupportsBreaks(""), false);
});

test("the exam station cap matches the number the warning copy prints", () => {
  assert.equal(MAX_EXAM_STATIONS, 12);
});

test("reading time is held to what the server keeps, and defaults to its default", () => {
  assert.equal(DEFAULT_READING_MINUTES, 3);
  assert.equal(clampReadingMinutes(0), 1);
  assert.equal(clampReadingMinutes(99), 30);
  assert.equal(clampReadingMinutes(2), 2);
  assert.equal(clampReadingMinutes(Number.NaN), 3);
});
