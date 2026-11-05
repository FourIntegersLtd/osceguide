import assert from "node:assert/strict";
import test from "node:test";
import { assessWordsFor } from "@/domains/assess/vocabulary";

test("a hire workspace reads employer words", () => {
  const w = assessWordsFor("hire");
  assert.deepEqual([w.Sittings, w.scheduleSitting, w.Trainees, w.addPeople], ["Assessments", "Schedule an assessment", "Candidates", "Add candidates"]);
});

test("an institution workspace, or none, reads institution words", () => {
  for (const surface of ["assess", undefined] as const) {
    const w = assessWordsFor(surface);
    assert.deepEqual([w.Sittings, w.scheduleSitting, w.Trainees], ["Sittings", "Schedule a sitting", "Trainees"]);
  }
});
