import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { nextRubricTitle } from "@/capabilities/authoring/rubrics/rubricTitle";

describe("nextRubricTitle", () => {
  it("sends the trimmed title when it actually changed", () => {
    assert.equal(nextRubricTitle("Old title", "  New title  "), "New title");
  });

  it("sends nothing when the typed title is the same as the rubric's, once trimmed", () => {
    assert.equal(nextRubricTitle("Same title", "Same title"), null);
    assert.equal(nextRubricTitle("Same title", "  Same title  "), null);
  });

  it("sends nothing for a title that is blank once trimmed", () => {
    assert.equal(nextRubricTitle("Old title", ""), null);
    assert.equal(nextRubricTitle("Old title", "   "), null);
  });
});
