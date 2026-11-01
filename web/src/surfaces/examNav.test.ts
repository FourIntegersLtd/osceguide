import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { examDetail, examForFilter } from "@/surfaces/examNav";

describe("examDetail", () => {
  const now = new Date(2026, 9, 11);
  it("is the exam code alone until a date is set", () => {
    assert.equal(examDetail("sca", null, now), "SCA");
    assert.equal(examDetail(null, "2026-12-01", now), null);
  });

  it("puts the weeks left under the workspace name", () => {
    assert.equal(examDetail("sca", "2026-11-22", now), "SCA · 6 weeks to go");
    assert.equal(examDetail("sca", "2026-10-18", now), "SCA · 1 week to go");
    assert.equal(examDetail("sca", "2026-10-14", now), "SCA · 3 days to go");
  });

  it("shares the dashboard's wording for today and past", () => {
    assert.equal(examDetail("sca", "2026-10-11", now), "SCA · Exam day");
    assert.equal(examDetail("sca", "2026-10-01", now), "SCA · Exam date has passed");
  });
});

describe("the exam a nav or route gate filters by", () => {
  it("is '' while the dashboard loads (hide exam-specific items) and undefined once it answered with none or failed (filter nothing)", () => {
    assert.equal(examForFilter({ code: null, loading: true }), "");
    assert.equal(examForFilter({ code: null, loading: false }), undefined);
  });

  it("is the exam itself once known, including while a reload is in flight", () => {
    assert.equal(examForFilter({ code: "plab", loading: false }), "plab");
    assert.equal(examForFilter({ code: "sca", loading: true }), "sca");
  });
});
