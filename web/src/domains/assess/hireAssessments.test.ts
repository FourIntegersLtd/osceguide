import assert from "node:assert/strict";
import test from "node:test";
import { EMPLOYER_WORDS } from "@/capabilities/assess-words/vocabulary";
import { assessmentBuckets, assessmentNoExam, bucketLabel, sittingNextStep, type NextStepSitting } from "@/domains/assess/hireAssessments";

const base: NextStepSitting = { id: "s1", status: "scheduled", mode: "exam", scheduled_for: "2026-12-04T09:00:00Z", circuit_count: 2, circuits: [{ supervisor_user_id: "u1" }, { supervisor_user_id: "u2" }] };
const w = EMPLOYER_WORDS;

test("next step chip says Running, Add assessors, Decide N, Released", () => {
  assert.deepEqual(sittingNextStep({ ...base, status: "in_progress" }, w, undefined), { label: "Running", tone: "live" });
  assert.deepEqual(sittingNextStep({ ...base, circuits: [{ supervisor_user_id: "u1" }, { supervisor_user_id: null }] }, w, undefined), { label: "Add assessors", tone: "warn" });
  assert.deepEqual(sittingNextStep({ ...base, status: "completed" }, w, { sat: 5, not_decided: 3, draft: 0, signed_off: 2, released: 0 }), { label: "Decide 3", tone: "info" });
  assert.deepEqual(sittingNextStep({ ...base, status: "completed" }, w, { sat: 5, not_decided: 0, draft: 0, signed_off: 0, released: 5 }), { label: "Released", tone: "ok" });
  assert.deepEqual(sittingNextStep({ ...base, status: "completed", mode: "training" }, w, undefined), { label: "Released", tone: "ok" });
});

test("other next steps", () => {
  assert.deepEqual(sittingNextStep({ ...base, circuit_count: 0, circuits: [] }, w, undefined), { label: "Add rotations", tone: "warn" });
  assert.deepEqual(sittingNextStep({ ...base, scheduled_for: null }, w, undefined), { label: "Set a date", tone: "warn" });
  assert.deepEqual(sittingNextStep(base, w, undefined), { label: "Scheduled", tone: "info" });
  assert.deepEqual(sittingNextStep({ ...base, status: "cancelled" }, w, undefined), { label: "Cancelled", tone: "neutral" });
  assert.deepEqual(sittingNextStep({ ...base, status: "completed" }, w, { sat: 5, not_decided: 0, draft: 0, signed_off: 3, released: 2 }), { label: "Release 3", tone: "info" });
});

test("pills sort upcoming, waiting for decisions and past, with counts", () => {
  const rows = [
    { ...base, id: "a" },
    { ...base, id: "b", status: "in_progress" },
    { ...base, id: "c", status: "completed" },
    { ...base, id: "d", status: "completed", mode: "training" },
    { ...base, id: "e", status: "cancelled" },
  ];
  const index = { c: { sat: 4, not_decided: 3, draft: 0, signed_off: 1, released: 0 } };
  const b = assessmentBuckets(rows, index);
  assert.deepEqual([b.upcoming.length, b.waiting.length, b.past.length], [2, 1, 2]);
  assert.equal(bucketLabel("waiting", b), "Waiting for decisions 1");
  assert.equal(bucketLabel("upcoming", b), "Upcoming 2");
  assert.equal(bucketLabel("past", b), "Past 2");
});

test("a completed exam with no results row yet still waits for decisions", () => {
  const b = assessmentBuckets([{ ...base, id: "c", status: "completed" }], {});
  assert.equal(b.waiting.length, 1);
});

test("no exam state says why Schedule is off", () => {
  assert.deepEqual(assessmentNoExam(w), {
    title: "You need an exam first",
    body: "An assessment runs an exam. Start from one of ours or build your own.",
    action: "Set up an exam",
    why: "Scheduling needs an exam available for scheduling.",
  });
});
