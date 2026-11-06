import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  codeTakenMessage,
  NEW_EXAM_STEPS,
  toMinutes,
  resumeStep,
  timingProblem,
  timingsLine,
} from "@/capabilities/authoring/exams/newExam";

describe("New exam sheet", () => {
  it("names its four steps", () => {
    assert.deepEqual(NEW_EXAM_STEPS, ["Name", "Marking scheme", "Timings", "Publish"]);
  });
  it("resumes at the first step still to do", () => {
    assert.equal(resumeStep(null), 0);
    assert.equal(resumeStep({ rubric_version_id: null }), 1);
    assert.equal(resumeStep({ rubric_version_id: "rv1" }), 2);
  });
  it("holds timings to the board's ranges", () => {
    assert.equal(timingProblem({ reading: "3", simulation: "10" }), null);
    assert.equal(timingProblem({ reading: "0", simulation: "10" }), "Reading time must be 1 to 30 minutes.");
    assert.equal(timingProblem({ reading: "31", simulation: "10" }), "Reading time must be 1 to 30 minutes.");
    assert.equal(timingProblem({ reading: "3", simulation: "181" }), "Consultation must be 1 to 180 minutes.");
    assert.equal(timingProblem({ reading: "", simulation: "10" }), "Reading time must be 1 to 30 minutes.");
  });
  it("summarises timings", () => {
    assert.equal(timingsLine({ reading: "3", simulation: "10" }), "3 min reading · 10 min consultation");
  });
  it("holds the break to 1 to 60 minutes, and lets it be left blank", () => {
    assert.equal(timingProblem({ reading: "3", simulation: "10", breakMin: "5" }), null);
    assert.equal(timingProblem({ reading: "3", simulation: "10", breakMin: "" }), null);
    assert.equal(timingProblem({ reading: "3", simulation: "10", breakMin: "61" }), "Break must be 1 to 60 minutes.");
    assert.equal(timingProblem({ reading: "3", simulation: "10", breakMin: "0.5" }), "Break must be 1 to 60 minutes.");
  });
  it("adds the break to the summary when the exam has one", () => {
    assert.equal(
      timingsLine({ reading: "3", simulation: "10", breakMin: "5" }),
      "3 min reading · 10 min consultation · 5 min break",
    );
  });
  it("shows stored seconds as minutes", () => {
    assert.equal(toMinutes(180), 3);
    assert.equal(toMinutes("600"), 10);
  });
});

describe("codeTakenMessage", () => {
  it("names the exam that holds the code and where to find it", () => {
    assert.equal(
      codeTakenMessage("csm", "Consultation skills mock", "draft"),
      'The code "csm" is already used by the draft "Consultation skills mock". Open it from Exams and choose Continue setup, or pick another code.',
    );
    assert.equal(
      codeTakenMessage("csm", "Consultation skills mock", "published"),
      'The code "csm" is already used by the exam "Consultation skills mock". Pick another code.',
    );
  });
});
