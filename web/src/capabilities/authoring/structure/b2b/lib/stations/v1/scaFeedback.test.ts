import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { scaFeedbackTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/scaFeedback";

describe("SCA feedback template", () => {
  it("ends with the priorities alone: no per-domain summaries or language notes", () => {
    const sections = scaFeedbackTemplateV1().sections;
    const last = sections[sections.length - 1];
    assert.equal(last?.title, "Priorities");
    assert.deepEqual(
      last?.blocks.map((block) => [block.id, block.label]),
      [["actionable_feedback_overall_priorities", "Overall priorities"]],
    );
    // No other block anywhere writes into the actionable feedback: its ids are the stored keys.
    const ids = sections.flatMap((section) => section.blocks.map((block) => block.id));
    assert.deepEqual(
      ids.filter((id) => id.startsWith("actionable_feedback_")),
      ["actionable_feedback_overall_priorities"],
    );
  });
});
