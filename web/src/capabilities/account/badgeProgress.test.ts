import assert from "node:assert/strict";
import { test } from "node:test";
import { badgeProgress } from "./badgeProgress";

test("a newcomer has no badge and is five stations from the first", () => {
  const progress = badgeProgress(0);
  assert.equal(progress.earned, 0);
  assert.equal(progress.toNext, 5);
  assert.deepEqual(progress.milestones, [5, 10, 15, 20, 25, 30, 35, 40]);
});

test("twelve stations is two badges, three from the next", () => {
  const progress = badgeProgress(12);
  assert.equal(progress.earned, 2);
  assert.equal(progress.toNext, 3);
});

test("landing exactly on a badge counts it and starts the next five", () => {
  const progress = badgeProgress(10);
  assert.equal(progress.earned, 2);
  assert.equal(progress.toNext, 5);
});

test("the row grows so the next unearned milestone is always shown", () => {
  assert.equal(badgeProgress(47).milestones.at(-1), 50);
});
