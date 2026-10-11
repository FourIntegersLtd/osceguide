import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { examCountdown } from "@/foundation/ui/examCountdown";
import { isExamWeek } from "@/domains/train/dashboard/examDate";

// Local times, because the calendar shows the learner's own day.
const LATE_EVENING = new Date(2026, 8, 21, 23, 30).getTime();
const MORNING = new Date(2026, 8, 21, 8, 0).getTime();

describe("exam date countdown", () => {
  it("counts whole days to the day the calendar shows, whatever the hour or zone", () => {
    assert.equal(examCountdown("2026-09-22", LATE_EVENING), "1 day to go");
    assert.equal(examCountdown("2026-09-22", MORNING), "1 day to go");
    assert.equal(examCountdown("2026-09-24", LATE_EVENING), "3 days to go");
  });

  it("counts six weeks, and one week, with the right plural", () => {
    assert.equal(examCountdown("2026-11-02", MORNING), "6 weeks to go");
    assert.equal(examCountdown("2026-09-28", MORNING), "1 week to go");
  });

  it("says Exam day on the day itself, and reports a passed date", () => {
    assert.equal(examCountdown("2026-09-21", LATE_EVENING), "Exam day");
    assert.equal(examCountdown("2026-09-20", MORNING), "Exam date has passed");
  });

  it("says nothing when there is no date", () => {
    assert.equal(examCountdown(null, MORNING), undefined);
    assert.equal(isExamWeek(null, MORNING), false);
  });

  it("opens the good-luck window from the exam day to seven days out", () => {
    assert.equal(isExamWeek("2026-09-21", LATE_EVENING), true);
    assert.equal(isExamWeek("2026-09-28", MORNING), true);
    assert.equal(isExamWeek("2026-09-29", MORNING), false);
    assert.equal(isExamWeek("2026-09-20", MORNING), false);
  });
});
