import assert from "node:assert/strict";
import { test } from "node:test";
import { briefBlockEntries } from "./briefBlockMeta";
import type { AudienceSection } from "./sectionsByAudience";

function section(id: string, blockIds: string[]): AudienceSection {
  return {
    id,
    title: "Doctor Information",
    audience: "candidate",
    blocks: blockIds.map((blockId) => ({
      id: blockId,
      label: blockId.replace(/_/g, " "),
      type: "list",
      role: "candidate_brief",
      value: ["something"],
      fields: null,
    })),
  };
}

test("the SCA brief reads in the legacy order: photos, biodata, notes, medications, history, social, investigations", () => {
  const entries = briefBlockEntries([
    section("doctor_information", [
      "doctor_patient_biodata",
      "recent_notes",
      "current_medications",
      "past_medical_history",
      "recent_investigations",
      "social_history",
      "doctor_photos",
    ]),
  ]);
  assert.deepEqual(
    entries.map((entry) => entry.title),
    [
      "Photos",
      "Patient Biodata",
      "Recent Notes",
      "Current Medications",
      "Past Medical History",
      "Social History",
      "Recent Investigations",
    ],
  );
});

test("PLAB and CASC task blocks take their legacy headings", () => {
  const plab = briefBlockEntries([section("doctor_information", ["doctor_identity", "task_instructions"])]);
  assert.deepEqual(
    plab.map((entry) => entry.title),
    ["Your Role", "Your Task"],
  );
  const casc = briefBlockEntries([section("doctor_information", ["doctor_task"])]);
  assert.equal(casc[0]!.title, "Your Role");
});

test("a block the map does not know keeps its label and trails in template order", () => {
  const entries = briefBlockEntries([
    section("doctor_information", ["a_custom_block", "another_custom_block", "doctor_patient_biodata"]),
  ]);
  assert.deepEqual(
    entries.map((entry) => entry.title),
    ["Patient Biodata", "a custom block", "another custom block"],
  );
});
