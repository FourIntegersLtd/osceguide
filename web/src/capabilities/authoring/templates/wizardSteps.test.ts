import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { wizardSteps } from "@/capabilities/authoring/templates/wizardSteps";

describe("wizardSteps", () => {
  it("starts open on the first screen", () => {
    assert.deepEqual(wizardSteps("start", false), [
      { id: "start", label: "Start", state: "todo", note: "Choose exam and layout" },
      { id: "sections", label: "Sections & fields", state: "todo", note: "Then save a draft" },
    ]);
  });
  it("marks the start done once on the sections", () => {
    assert.deepEqual(wizardSteps("sections", true)[0], { id: "start", label: "Start", state: "done", note: "Exam, name, layout" });
  });
});
