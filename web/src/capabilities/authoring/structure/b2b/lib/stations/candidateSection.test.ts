import assert from "node:assert/strict";
import { test } from "node:test";
import { filledCandidateSection, sectionHasContent } from "@/capabilities/authoring/lib/b2cStationContentScope";
import type { StationSection } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

const section = (id: string, audience: string, blocks: Array<{ id: string; role?: string }>) =>
  ({ id, title: `Section ${id}`, audience, blocks }) as unknown as StationSection;

const candidate = section("c", "candidate", [{ id: "brief" }, { id: "points" }]);

test("a candidate section with no text is blank, so an old flat reading brief is still the candidate's", () => {
  assert.equal(sectionHasContent({ reading_brief: "Old flat brief", brief: "  ", points: [] }, candidate), false);
  assert.equal(sectionHasContent({ brief: "Read this" }, candidate), true);
  assert.equal(sectionHasContent({ points: ["", "one"] }, candidate), true);
});

test("false and a list of blank strings count as written, as on the server", () => {
  assert.equal(sectionHasContent({ brief: false }, candidate), true);
  assert.equal(sectionHasContent({ points: [""] }, candidate), true);
  assert.equal(sectionHasContent({ points: {} }, candidate), false);
});

test("an examiner-role block filled in a candidate section does not hide the brief editor", () => {
  const filed = section("c", "candidate", [{ id: "brief" }, { id: "answer", role: "examiner" }, { id: "secret", role: "hidden" }]);
  const sections = [filed];
  assert.equal(filledCandidateSection(sections, { answer: "Model answer", secret: "x" }), null);
  assert.equal(filledCandidateSection(sections, { brief: "Read this" }), filed);
});

test("a filled second candidate section is the candidate's brief", () => {
  const second = section("c2", "candidate", [{ id: "more" }]);
  const sections = [candidate, section("p", "patient", [{ id: "script" }]), second];
  assert.equal(filledCandidateSection(sections, { more: "Read this too", script: "s" }), second);
  assert.equal(filledCandidateSection(sections, { script: "s" }), null);
});

test("a section with no explicit audience is not the candidate's, whatever its id", () => {
  const legacy = section("sec_case", "", [{ id: "brief" }]);
  assert.equal(filledCandidateSection([legacy], { brief: "Read this" }), null);
});

test("a custom section stored nested is read, as on the server", () => {
  const pack = section("brief_pack", "candidate", [{ id: "brief" }]);
  assert.equal(sectionHasContent({ brief_pack: { brief: "Read this" } }, pack), true);
  assert.equal(sectionHasContent({ brief_pack: { brief: " " } }, pack), false);
});

test("a nested section falls back to the block stored flat at the top level", () => {
  const doctor = section("doctor_information", "candidate", [{ id: "doctor_notes" }]);
  assert.equal(sectionHasContent({ doctor_information: {}, doctor_notes: "Read this" }, doctor), true);
  assert.equal(sectionHasContent({ doctor_information: { notes: "Bare key" } }, doctor), true);
  assert.equal(sectionHasContent({ doctor_information: {} }, doctor), false);
});
