import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { examResumePath, rubricEditPath } from "@/capabilities/authoring/templates/paths";

const hrefFor = (path: string) => `/app/acme${path}`;

describe("returning to the New exam sheet", () => {
  it("carries the exam through the builder path", () => {
    assert.equal(rubricEditPath(hrefFor, "r1", 2, "ex 9"), "/app/acme/authoring/rubrics/r1/versions/2?exam=ex%209");
    assert.equal(rubricEditPath(hrefFor, "r1", 2), "/app/acme/authoring/rubrics/r1/versions/2");
  });
  it("resumes the exam sheet", () => {
    assert.equal(examResumePath(hrefFor, "ex9"), "/app/acme/authoring/exams/new?exam=ex9");
  });
});
