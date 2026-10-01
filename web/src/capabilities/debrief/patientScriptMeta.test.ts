import assert from "node:assert/strict";
import { test } from "node:test";
import type { AudienceSection } from "@/capabilities/attempt-runner/material/sectionsByAudience";
import { patientScriptTabs, scriptLines } from "./patientScriptMeta";

function patientSection(blocks: Record<string, unknown>): AudienceSection {
  return {
    id: "patient",
    title: "Patient",
    audience: "patient",
    blocks: Object.entries(blocks).map(([blockId, value]) => ({
      id: blockId,
      label: blockId.replace(/_/g, " "),
      type: Array.isArray(value) ? "list" : "longText",
      role: "patient",
      value,
      fields: null,
    })),
  };
}

test("the patient script sorts onto the legacy History, ICE and Persona tabs", () => {
  const tabs = patientScriptTabs([
    patientSection({
      patient_biodata: "Sam, 34",
      opening_sentence: "My hands are so sore.",
      idea: "It is the gloves",
      questions: ["Can I keep working?"],
      persona: "Anxious but polite",
      examination_findings: "Dry fissured skin",
      concerns: "",
    }),
  ]);

  assert.deepEqual(tabs.history.map((entry) => entry.title), ["Your opening sentence", "examination findings"]);
  assert.deepEqual(tabs.ice.map((entry) => entry.title), ["Ideas", "Questions you may ask"]);
  assert.deepEqual(tabs.persona.map((entry) => entry.title), ["Your personality & approach"]);
});

test("a multi-line text reads as one line per bullet", () => {
  assert.deepEqual(scriptLines("Started a month ago\n\n Worse at work "), ["Started a month ago", "Worse at work"]);
});
