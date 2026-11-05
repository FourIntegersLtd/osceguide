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

test("hire says assessor and intake where an institution says supervisor and year group", () => {
  const pick = (surface: "hire" | "assess") => {
    const w = assessWordsFor(surface);
    return [w.Supervisors, w.YearGroup, w.Exams];
  };
  assert.deepEqual(pick("hire"), ["Assessors", "Intake", "Exams"]);
  assert.deepEqual(pick("assess"), ["Supervisors", "Year group", "Exams"]);
});

test("both arms call the two modes of sitting Formal exam and Training", () => {
  for (const surface of ["hire", "assess"] as const) {
    const w = assessWordsFor(surface);
    assert.deepEqual([w.formalExam, w.training], ["Formal exam", "Training"]);
  }
});
