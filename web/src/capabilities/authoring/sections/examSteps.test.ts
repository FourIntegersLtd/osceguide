import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { examNextAction, examSteps } from "@/capabilities/authoring/sections/examSteps";

describe("examSteps", () => {
  it("a draft with no scheme asks for one", () => {
    assert.deepEqual(examSteps({ status: "draft", rubric_version_id: null }), [
      { id: "scheme", label: "Pick marking scheme", state: "todo", note: "Not chosen" },
      { id: "publish", label: "Publish", state: "todo", note: "Draft" },
    ]);
    assert.deepEqual(examNextAction({ status: "draft" }), { id: "pick-scheme", line: "Pick a marking scheme, then publish." });
  });
  it("a draft with a scheme is ready to publish", () => {
    assert.equal(examSteps({ status: "draft", rubric_version_id: "rv1" })[0]?.state, "done");
    assert.deepEqual(examNextAction({ status: "draft", rubric_version_id: "rv1" }), {
      id: "publish",
      line: "Publish this exam to run sittings against it.",
    });
  });
  it("a published exam points at programmes; a retired one at nothing", () => {
    const live = examSteps({ status: "published", rubric_version_id: "rv1" });
    assert.deepEqual(live[1], { id: "publish", label: "Publish", state: "done", note: "Live" });
    assert.equal(examNextAction({ status: "published", rubric_version_id: "rv1" }).id, "programme");
    assert.equal(examSteps({ status: "retired" })[1]?.note, "Retired");
    assert.equal(examNextAction({ status: "retired" }).id, "none");
  });
});
