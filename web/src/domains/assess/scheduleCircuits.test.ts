import assert from "node:assert/strict";
import { test } from "node:test";
import { rotationAssessors, rotationChip, rotationTime } from "@/domains/assess/sittingWords";

test("a rotation's chip says what to do next", () => {
  const base = { started_at: null, ended_at: null, supervisor_user_id: "u", trainee_count: 1 };
  assert.deepEqual(rotationChip({ ...base, supervisor_user_id: null }), { label: "Needs an assessor", tone: "warn" });
  assert.deepEqual(rotationChip(base), { label: "Ready", tone: "info" });
  assert.deepEqual(rotationChip({ ...base, started_at: "2026-11-20T09:00:00Z" }), { label: "Running", tone: "live" });
  assert.deepEqual(rotationChip({ ...base, started_at: "a", ended_at: "b" }), { label: "Finished", tone: "ok" });
});

test("a rotation's time runs from the start for its stations and breaks", () => {
  const timing = { reading_minutes: 1, simulation_minutes: 8, break_minutes: 1, breaks: [2], break_lengths: [{ after_station: 2, minutes: 5 }] };
  const start = new Date(2026, 10, 20, 9, 0).toISOString();
  assert.equal(rotationTime(start, 5, timing), "09:00 to 09:50");
  assert.equal(rotationTime(null, 5, timing), "");
});

test("only an employer's rotation row lists its assessors", () => {
  assert.deepEqual(rotationAssessors(["Dan Lowe", "Sara Khan"], true), ["Dan Lowe, Sara Khan"]);
  assert.deepEqual(rotationAssessors(["Dan Lowe"], false), []);
  assert.deepEqual(rotationAssessors([], true), []);
});
