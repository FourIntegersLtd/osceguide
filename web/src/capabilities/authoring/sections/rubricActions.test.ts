import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { rubricVersionActions } from "@/capabilities/authoring/sections/rubricActions";

const own = { platformOwned: false, orgScope: true };

describe("rubricVersionActions", () => {
  it("offers publish on a draft only", () => {
    assert.deepEqual(rubricVersionActions("draft", own), { publish: true, archive: false });
    assert.deepEqual(rubricVersionActions("archived", own), { publish: false, archive: false });
  });
  it("offers archive on a published version only", () => {
    assert.deepEqual(rubricVersionActions("published", own), { publish: false, archive: true });
  });
  it("offers an organisation nothing on a platform rubric", () => {
    const locked = { platformOwned: true, orgScope: true };
    assert.deepEqual(rubricVersionActions("draft", locked), { publish: false, archive: false });
    assert.deepEqual(rubricVersionActions("published", locked), { publish: false, archive: false });
  });
  it("leaves staff their own writes on a platform rubric", () => {
    const staff = { platformOwned: true, orgScope: false };
    assert.deepEqual(rubricVersionActions("draft", staff), { publish: true, archive: false });
  });
});
