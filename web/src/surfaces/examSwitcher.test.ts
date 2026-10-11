import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { examDetail, examSwitcherView } from "@/surfaces/examSwitcher";

describe("examSwitcherView", () => {
  it("offers a retry when the exams could not be read and none are known", () => {
    assert.equal(examSwitcherView({ consumer: true, codes: [], error: new Error("502") }), "failed");
  });

  it("keeps the switcher when a reload fails but the exams are known", () => {
    assert.equal(examSwitcherView({ consumer: true, codes: ["sca", "plab"], error: new Error("502") }), "switcher");
  });

  it("shows nothing for an institution member or a healthy single exam", () => {
    assert.equal(examSwitcherView({ consumer: false, codes: [], error: new Error("x") }), "none");
    assert.equal(examSwitcherView({ consumer: true, codes: ["sca"], error: null }), "none");
  });
});

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
