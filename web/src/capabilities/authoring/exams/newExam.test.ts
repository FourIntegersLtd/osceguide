import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  createWithFreshCode,
  generateExamCode,
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

describe("generateExamCode", () => {
  it("slugs the name and adds four random characters", () => {
    const code = generateExamCode("Paediatrics block");
    assert.match(code, /^PAEDIATRICS-BLOCK-[A-Z0-9]{4}$/);
    assert.match(generateExamCode("  Final MB (OSCE) 2026!! "), /^FINAL-MB-OSCE-2026-[A-Z0-9]{4}$/);
  });
  it("always fits the api pattern and differs per call", () => {
    for (const name of ["", "!!!", "x".repeat(80), "Ünï côdé"]) {
      assert.match(generateExamCode(name), /^[A-Z0-9-]{2,32}$/);
    }
    assert.notEqual(generateExamCode("Paediatrics"), generateExamCode("Paediatrics"));
    assert.ok(generateExamCode("x".repeat(80)).length <= 32);
  });
});

describe("createWithFreshCode", () => {
  const taken = (cause: unknown) => cause === "taken";
  it("retries a taken code up to three times with a new code each time", async () => {
    const seen: string[] = [];
    const made = await createWithFreshCode("Mock", taken, async (code) => {
      seen.push(code);
      if (seen.length < 4) throw "taken";
      return code;
    });
    assert.equal(seen.length, 4);
    assert.equal(new Set(seen).size, 4);
    assert.equal(made, seen[3]);
  });
  it("gives a plain error without a code after the retries", async () => {
    await assert.rejects(
      createWithFreshCode("Mock", taken, async () => {
        throw "taken";
      }),
      (e: Error) => !/code/i.test(e.message) && e.message.length > 0,
    );
  });
  it("passes any other failure through", async () => {
    await assert.rejects(createWithFreshCode("Mock", taken, async () => { throw new Error("boom"); }), /boom/);
  });
});
