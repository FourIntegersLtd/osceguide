import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { rubricNextAction, rubricSteps } from "@/capabilities/authoring/rubrics/rubricSteps";

const clean = { status: "draft", dirty: false, checking: false, problems: 0, promptMissing: false };

describe("rubricSteps", () => {
  it("a clean saved draft is ready to publish", () => {
    assert.deepEqual(rubricSteps(clean), [
      { id: "draft", label: "Draft", state: "done", note: "Saved" },
      { id: "preview", label: "Preview", state: "done", note: "No problems" },
      { id: "publish", label: "Publish", state: "todo", note: "Not published" },
    ]);
    assert.deepEqual(rubricNextAction(clean), { id: "publish", line: "Looks right in the preview. Publish this version." });
  });
  it("problems come first, then instructions, then saving", () => {
    assert.equal(rubricSteps({ ...clean, problems: 2 })[1]?.note, "2 problems");
    assert.deepEqual(rubricNextAction({ ...clean, problems: 1, dirty: true }), { id: "fix", line: "Fix 1 problem below to publish." });
    assert.equal(rubricNextAction({ ...clean, promptMissing: true }).id, "instructions");
    assert.equal(rubricSteps({ ...clean, dirty: true })[0]?.state, "attention");
    assert.equal(rubricNextAction({ ...clean, dirty: true }).id, "save");
    assert.equal(rubricNextAction({ ...clean, checking: true }).id, "wait");
  });
  it("a published version is done and read-only", () => {
    const steps = rubricSteps({ ...clean, status: "published" });
    assert.deepEqual(steps.map((s) => s.state), ["done", "done", "done"]);
    assert.equal(steps[2]?.note, "Live");
    assert.equal(rubricNextAction({ ...clean, status: "published" }).id, "none");
  });
});
