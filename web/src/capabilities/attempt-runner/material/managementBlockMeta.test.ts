import assert from "node:assert/strict";
import { test } from "node:test";
import { MODEL_ANSWER_HEADING, managementLayout, modelAnswerLine } from "./managementBlockMeta";
import type { AudienceSection } from "./sectionsByAudience";

function section(id: string, title: string, blocks: Record<string, unknown>): AudienceSection {
  return {
    id,
    title,
    audience: "examiner",
    blocks: Object.entries(blocks).map(([blockId, value]) => ({
      id: blockId,
      label: blockId.replace(/_/g, " "),
      type: Array.isArray(value) ? "list" : "longText",
      role: "examiner",
      value,
      fields: null,
    })),
  };
}

test("an SCA model answer reads as the legacy screen: explanation, clinical assessment, then the collapsible stages", () => {
  const layout = managementLayout([
    section("management_plan", "Management Plan", {
      explanation: "Irritant contact dermatitis.",
      assessment: ["Examine both hands"],
      social_concerns: ["Worried about work"],
      ice: ["Thinks it is the gloves"],
      immediate_actions: [],
      pharmacological_treatment: ["Emollient"],
      follow_up: "Review in two weeks",
      additional_notes: "",
    }),
  ]);

  assert.deepEqual(layout.lead.map((entry) => entry.title), ["explanation"]);
  assert.deepEqual(
    layout.groups.map((group) => [group.title, group.collapsible, group.entries.map((entry) => entry.title)]),
    [
      ["Clinical assessment", false, ["Assessment steps"]],
      ["Social & patient concerns", true, ["social concerns", "ICE response"]],
      ["Treatment & actions", true, ["Medications"]],
      ["Patient education & follow-up", true, ["follow up"]],
    ],
  );
  assert.equal(layout.groups[2]!.entries[0]!.tone, "management");
});

test("a block the map does not know is grouped under its own section's title, after the legacy groups", () => {
  const layout = managementLayout([
    section("key_concerns", "Key Concerns", { key_concerns: ["Open fracture"] }),
    section("management_plan", "Management Plan", { assessment: ["Neurovascular status"] }),
  ]);

  assert.deepEqual(
    layout.groups.map((group) => [group.title, group.collapsible]),
    [
      ["Clinical assessment", false],
      ["Key Concerns", true],
    ],
  );
});

test("the explanation reads as information, not a warning: no amber tone leads the model answer", () => {
  const layout = managementLayout([
    section("management_plan", "Management Plan", { explanation: "Irritant contact dermatitis.", description: "A rash." }),
  ]);
  assert.deepEqual(layout.lead.map((entry) => entry.tone), ["history", "history"]);
});

test("the model answer is headed by what it shows, with one line that adds the action", () => {
  assert.equal(MODEL_ANSWER_HEADING, "What a thorough plan covers");
  assert.equal(modelAnswerLine("Contact dermatitis"), "Contact dermatitis. Compare it with your transcript.");
});
