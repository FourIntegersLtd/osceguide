import assert from "node:assert/strict";
import { test } from "node:test";
import { managementLayout } from "./managementBlockMeta";
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
      ["Clinical Assessment", false, ["Assessment Steps"]],
      ["Social & Patient Concerns", true, ["social concerns", "ICE Response"]],
      ["Treatment & Actions", true, ["Medications"]],
      ["Patient Education & Follow-up", true, ["follow up"]],
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
      ["Clinical Assessment", false],
      ["Key Concerns", true],
    ],
  );
});
