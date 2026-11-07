import assert from "node:assert/strict";
import test from "node:test";
import type { StaffSection } from "@/domains/assess/sessions/api";
import { candidateSections, untemplatedBrief } from "@/domains/assess/sessions/supervisorBrief";

function section(audience: string, ...roles: string[]): StaffSection {
  return {
    id: audience,
    title: audience,
    audience,
    blocks: roles.map((role, i) => ({ id: `${audience}-${i}`, label: role, type: "longText", role, value: role })),
  };
}

test("only the candidate's blocks reach the supervisor brief", () => {
  const shown = candidateSections([
    section("candidate", "candidate_brief", "hidden", "examiner"),
    section("patient", "patient_script"),
    section("examiner", "examiner"),
    section("faculty", "faculty", "debrief"),
  ]);
  assert.deepEqual(
    shown.map((s) => [s.audience, s.blocks.map((b) => b.role)]),
    [["candidate", ["candidate_brief"]]],
  );
});

test("a candidate section left with only held blocks is dropped", () => {
  assert.deepEqual(candidateSections([section("candidate", "hidden")]), []);
});

test("an untemplated station shows its reading brief and no other field", () => {
  const content = { reading_brief: "Read this.", patient_script: "Secret", examiner_notes: "Marks" };
  assert.equal(untemplatedBrief(content), "Read this.");
  assert.equal(untemplatedBrief({ candidate_brief: "Older brief", patient_script: "Secret" }), "Older brief");
  assert.equal(untemplatedBrief({ patient_script: "Secret" }), null);
});
