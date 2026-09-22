import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  EXAM_PASSED,
  examCountdownSubtitle,
  examTimeRemaining,
  isExamWeek,
  parseExamDate,
} from "@/domains/train/dashboard/examDate";

// 2026-09-21T00:00:00Z, fixed so the countdowns are deterministic.
const NOW = Date.UTC(2026, 8, 21, 0, 0, 0);

describe("exam date countdown", () => {
  it("reads a bare date as UTC midnight", () => {
    assert.equal(parseExamDate("2026-11-02")?.getTime(), Date.UTC(2026, 10, 2));
    assert.equal(parseExamDate(null), null);
    assert.equal(parseExamDate(""), null);
  });

  it("counts six whole weeks to the exam, the way the old subtitle did", () => {
    // 42 days out — exactly six weeks.
    assert.equal(examCountdownSubtitle("2026-11-02", NOW), "6 weeks until your exam");
    assert.equal(examTimeRemaining("2026-11-02", NOW), "42 days");
    assert.equal(isExamWeek("2026-11-02", NOW), false);
  });

  it("says one week, not one weeks, seven days out", () => {
    assert.equal(examCountdownSubtitle("2026-09-28", NOW), "1 week until your exam");
    assert.equal(examTimeRemaining("2026-09-28", NOW), "7 days");
  });

  it("reports a passed exam date", () => {
    assert.equal(examTimeRemaining("2026-09-01", NOW), EXAM_PASSED);
    assert.equal(
      examCountdownSubtitle("2026-09-01", NOW),
      "Your exam date has passed. Keep practising to stay sharp.",
    );
    assert.equal(isExamWeek("2026-09-01", NOW), false);
  });

  it("opens the good-luck window inside seven days only", () => {
    assert.equal(isExamWeek("2026-09-24", NOW), true); // three days out
    assert.equal(isExamWeek("2026-09-28", NOW), true); // seven days out
    assert.equal(isExamWeek("2026-09-29", NOW), false); // eight days out
  });

  it("drops to hours and minutes on the last day", () => {
    assert.equal(examTimeRemaining("2026-09-21T00:30:00", NOW), "Less than 1h");
    assert.equal(examTimeRemaining("2026-09-21T03:00:00", NOW), "3h");
  });

  it("says nothing when there is no date", () => {
    assert.equal(examTimeRemaining(null, NOW), null);
    assert.equal(examCountdownSubtitle(null, NOW), undefined);
    assert.equal(isExamWeek(null, NOW), false);
  });
});
