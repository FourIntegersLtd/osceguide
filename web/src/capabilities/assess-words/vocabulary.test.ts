import assert from "node:assert/strict";
import test from "node:test";
import { assessWordsFor } from "@/capabilities/assess-words/vocabulary";

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

test("the circuit, home, my-training and lead words differ by arm", () => {
  const pick = (surface: "hire" | "assess") => {
    const w = assessWordsFor(surface);
    return [w.circuit, w.circuits, w.Circuit, w.Circuits, w.Home, w.MyTraining, w.leadSupervisor, w.LeadSupervisor];
  };
  assert.deepEqual(pick("hire"), ["rotation", "rotations", "Rotation", "Rotations", "Overview", "My assessments", "lead assessor", "Lead assessor"]);
  assert.deepEqual(pick("assess"), ["circuit", "circuits", "Circuit", "Circuits", "Home", "My training", "GP lead", "GP lead"]);
});

test("hire says assessor where an institution says examiner", () => {
  const pick = (surface: "hire" | "assess") => {
    const w = assessWordsFor(surface);
    return [w.examiner, w.examiners, w.Examiner];
  };
  assert.deepEqual(pick("hire"), ["assessor", "assessors", "Assessor"]);
  assert.deepEqual(pick("assess"), ["examiner", "examiners", "Examiner"]);
});
