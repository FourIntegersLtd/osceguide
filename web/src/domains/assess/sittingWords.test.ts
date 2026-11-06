import assert from "node:assert/strict";
import test from "node:test";
import { sittingChipTone, sittingWhen, sittingWhenAt } from "@/domains/assess/sittingWords";

const now = new Date(2026, 10, 5, 12, 0);

test("sittingWhen prints Today with the time, else the day and month", () => {
  assert.equal(sittingWhen(new Date(2026, 10, 5, 9, 0).toISOString(), now), "Today 09:00");
  assert.equal(sittingWhen(new Date(2026, 10, 12, 9, 0).toISOString(), now), "12 Nov");
  assert.equal(sittingWhen(new Date(2027, 2, 12, 9, 0).toISOString(), now), "12 Mar 2027");
  assert.equal(sittingWhen(null, now), "Not scheduled");
});

test("sittingWhenAt keeps the time on other days", () => {
  assert.equal(sittingWhenAt(new Date(2026, 11, 12, 9, 5).toISOString(), now), "12 Dec, 09:05");
});

test("status chip tones follow the board", () => {
  assert.equal(sittingChipTone("in_progress", false), "live");
  assert.equal(sittingChipTone("scheduled", false), "info");
  assert.equal(sittingChipTone("scheduled", true), "warn");
  assert.equal(sittingChipTone("completed", false), "neutral");
});
