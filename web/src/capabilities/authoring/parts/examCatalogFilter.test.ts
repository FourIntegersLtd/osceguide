import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { matchesExamFilter } from "@/capabilities/authoring/parts/examCatalogFilter";

describe("matchesExamFilter", () => {
  it("passes all rows when no exam selected", () => {
    assert.equal(matchesExamFilter("sca", "", {}), true);
    assert.equal(matchesExamFilter(null, "", {}), true);
  });

  it("matches exam code case-insensitively", () => {
    assert.equal(matchesExamFilter("SCA", "sca", {}), true);
    assert.equal(matchesExamFilter("plab", "sca", {}), false);
  });

  it("can include unscoped rows", () => {
    assert.equal(matchesExamFilter(null, "sca", {}), false);
    assert.equal(matchesExamFilter(null, "sca", { includeUnscoped: true }), true);
  });
});
