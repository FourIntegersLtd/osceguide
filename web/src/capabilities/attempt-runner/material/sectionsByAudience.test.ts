import assert from "node:assert/strict";
import { test } from "node:test";
import { asText, sectionLines, sectionsFor, type AudienceSection } from "./sectionsByAudience";

// The Ortho prioritisation review after the backend merged it by section id.
const review: AudienceSection[] = [
  {
    id: "basic_information",
    title: "Basic information",
    audience: "candidate",
    blocks: [
      { id: "clinical_scenario", label: "Scenario", type: "longText", role: "candidate_brief", value: "On call." },
      { id: "suggested_order_overview", label: "Suggested order", type: "longText", role: "examiner", value: "Open fracture first." },
    ],
  },
  {
    id: "suggested_list_order",
    title: "Suggested list order",
    audience: "examiner",
    blocks: [
      {
        id: "suggested_order",
        label: "Order",
        type: "groupedList",
        role: "examiner",
        value: { trauma: [{ title: "Bed 2", reasons: ["Open fracture"] }] },
      },
    ],
  },
];

test("the candidate part of a review leaves out examiner blocks filed in candidate sections", () => {
  assert.deepEqual(
    sectionsFor(review, "candidate").map((section) => [section.id, section.blocks.map((block) => block.id)]),
    [["basic_information", ["clinical_scenario"]]],
  );
});

test("the examiner part collects examiner blocks from every section", () => {
  assert.deepEqual(
    sectionsFor(review, "examiner").map((section) => [section.id, section.blocks.map((block) => block.id)]),
    [
      ["basic_information", ["suggested_order_overview"]],
      ["suggested_list_order", ["suggested_order"]],
    ],
  );
});

test("sections flatten to label lines for a voice agent", () => {
  assert.deepEqual(sectionLines(sectionsFor(review, "examiner")), [
    "Suggested order: Open fracture first.",
    "Order: trauma: title: Bed 2, reasons: Open fracture",
  ]);
});

test("rich values read as text in every shape", () => {
  assert.equal(asText([{ question: "First step?", answer: "ATLS" }]), "question: First step?, answer: ATLS");
  assert.equal(asText(["https://a.test/x.png", " "]), "https://a.test/x.png");
});
