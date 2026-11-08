import assert from "node:assert/strict";
import test from "node:test";
import { sittingChipTone, sittingDayLong, sittingHeadPrimary, sittingWhen, sittingWhenAt, sittingWhenLong } from "@/domains/assess/sittingWords";

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

test("sittingWhenLong and sittingDayLong print the long date, and say nothing for a bad one", () => {
  const at = new Date(2026, 10, 20, 9, 0).toISOString();
  assert.equal(sittingWhenLong(at), "Friday 20 November, 09:00");
  assert.equal(sittingDayLong(at), "20 November");
  assert.equal(sittingWhenLong(null, "Date to be confirmed"), "Date to be confirmed");
  assert.equal(sittingDayLong("nope"), "");
});

test("no institution noun is printed by these words, so hire reads them unchanged", () => {
  const printed = [sittingWhen(null), sittingWhenAt(null), sittingWhenLong(null), sittingChipTone("scheduled", false), sittingHeadPrimary({ status: "scheduled", scheduled_for: null })].join(" ");
  assert.equal(/sitting|trainee|supervisor|circuit|practi/i.test(printed.replace("schedule", "")), false);
});
