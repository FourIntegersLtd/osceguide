import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { latestOf } from "@/capabilities/authoring/sections/versions";

const v = (version: number, status: string) => ({ version, status });

describe("latestOf", () => {
  it("reads the newest of each, not the last in the array", () => {
    const { published, draft } = latestOf([
      v(3, "draft"),
      v(1, "published"),
      v(2, "published"),
    ]);
    assert.equal(published?.version, 2);
    assert.equal(draft?.version, 3);
  });

  it("counts anything that is neither published nor archived as the draft", () => {
    assert.equal(latestOf([v(1, "in_review")]).draft?.version, 1);
  });

  it("says so when everything has been archived", () => {
    assert.equal(latestOf([v(1, "archived"), v(2, "archived")]).archivedOnly, true);
  });

  it("does not call an empty template archived", () => {
    assert.equal(latestOf([]).archivedOnly, false);
  });
});
