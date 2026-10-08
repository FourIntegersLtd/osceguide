import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { canManageTemplate, latestOf, stationConfirmCopy, rubricVersionActions } from "@/capabilities/authoring/sections/versions";

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

describe("canManageTemplate", () => {
  it("lets an organisation manage its own templates and the platform manage its own", () => {
    assert.equal(canManageTemplate("org", "organization"), true);
    assert.equal(canManageTemplate("platform", "platform"), true);
  });

  it("offers an organisation no publish, archive or delete on a platform template", () => {
    assert.equal(canManageTemplate("org", "platform"), false);
  });
});

describe("stationConfirmCopy", () => {
  it("does not promise the station leaves the library when an older version may take over", () => {
    assert.match(stationConfirmCopy("archive"), /older version is still published/);
    assert.doesNotMatch(stationConfirmCopy("archive"), /is removed from the live library/);
  });
  it("warns that deleting the only version deletes the station", () => {
    assert.match(stationConfirmCopy("delete"), /only version, the station is deleted/);
  });
});

describe("rubricVersionActions", () => {
  it("offers publish on a draft only", () => {
    assert.deepEqual(rubricVersionActions("draft", "org", "org"), { publish: true, archive: false });
    assert.deepEqual(rubricVersionActions("archived", "org", "org"), { publish: false, archive: false });
  });
  it("offers archive on a published version only", () => {
    assert.deepEqual(rubricVersionActions("published", "org", "org"), { publish: false, archive: true });
  });
  it("offers an organisation nothing on a platform rubric, and staff their own writes", () => {
    assert.deepEqual(rubricVersionActions("draft", "org", "platform"), { publish: false, archive: false });
    assert.deepEqual(rubricVersionActions("draft", "platform", "platform"), { publish: true, archive: false });
  });
});
