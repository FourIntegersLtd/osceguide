import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { getAt, moveItem, parsePath, pathText, removeItem, setAt } from "@/capabilities/authoring/rubrics/jsonPath";
import {
  appendAt,
  identifierFrom,
  newField,
  newSection,
  readRating,
  uniqueIdentifier,
  withFieldType,
  withRatingField,
  withRatingKind,
  withScale,
  type RubricStructure,
} from "@/capabilities/authoring/rubrics/rubricEdits";
import { placeLabel, problemsAt, problemsFromDetails, problemsWithin } from "@/capabilities/authoring/rubrics/problems";
import { applyInstructionSuggestions } from "@/capabilities/authoring/rubrics/draftInstructions";
import { previewInputs, trialInputs } from "@/capabilities/authoring/rubrics/previewModel";

/** What `POST …/rubrics/copy` with no source answers: `authoring.blank_structure()`. */
function blankStructure(): RubricStructure {
  return {
    schemaVersion: 2,
    rating: { kind: "rag", field: "score" },
    sections: [
      {
        id: "domain_1",
        title: "Domain 1",
        kind: "domain",
        instructions: "",
        competencies: [{ id: "competency_1", label: "Competency 1", instructions: "" }],
        competencyFields: [
          { id: "score", type: "rating", role: "rating", label: "Rating" },
          { id: "evidence", type: "longText", role: "evidence", label: "Evidence" },
          { id: "explanation", type: "longText", role: "explanation", label: "Explanation" },
        ],
      },
    ],
  };
}

describe("paths", () => {
  it("writes and reads a path the way the backend writes a problem's", () => {
    assert.equal(pathText(["sections", 0, "competencies", 1, "id"]), "sections[0].competencies[1].id");
    assert.deepEqual(parsePath("sections[0].competencyFields[2].fields[0].id"), [
      "sections", 0, "competencyFields", 2, "fields", 0, "id",
    ]);
    assert.deepEqual(parsePath("display.tones[1].atLeast"), ["display", "tones", 1, "atLeast"]);
  });

  it("edits one place and keeps every key it does not know", () => {
    const copied = { ...blankStructure(), basedOn: { rubricId: "r1", version: 3, title: "SCA" } };
    const renamed = setAt(copied, ["sections", 0, "title"], "History");
    assert.equal(getAt(renamed, ["sections", 0, "title"]), "History");
    assert.deepEqual(renamed.basedOn, { rubricId: "r1", version: 3, title: "SCA" });
    assert.equal(getAt(copied, ["sections", 0, "title"]), "Domain 1");
    assert.equal("tones" in (setAt({ display: { tones: [] } }, ["display", "tones"], undefined).display as object), false);
  });

  it("removes and moves a list item", () => {
    const fields = ["sections", 0, "competencyFields"] as const;
    const moved = moveItem(blankStructure(), [...fields, 2], -1);
    assert.deepEqual((getAt(moved, fields) as Array<{ id: string }>).map((field) => field.id), ["score", "explanation", "evidence"]);
    const removed = removeItem(blankStructure(), [...fields, 1]);
    assert.deepEqual((getAt(removed, fields) as Array<{ id: string }>).map((field) => field.id), ["score", "explanation"]);
    assert.deepEqual(moveItem(blankStructure(), [...fields, 0], -1), blankStructure());
  });
});

describe("ids", () => {
  it("suggests an id from a label and never repeats one", () => {
    assert.equal(identifierFrom("History taking"), "history_taking");
    assert.equal(identifierFrom("3 things to do"), "item_3_things_to_do");
    assert.equal(uniqueIdentifier("notes", ["notes", "notes_2"]), "notes_3");
  });
});

describe("the rating", () => {
  it("starts each kind with values the backend accepts", () => {
    const range = withRatingKind(blankStructure(), "range");
    assert.deepEqual(range.rating, { kind: "range", field: "score", minimum: 0, maximum: 10, step: "integer" });
    assert.deepEqual(readRating(blankStructure()).scale, ["G", "A", "R"]);
  });

  it("drops tones and off-scale descriptors when moving to a scale", () => {
    let structure = setAt(blankStructure(), ["display", "tones"], [{ atLeast: 0.5, tone: "good" }]);
    structure = setAt(structure, ["sections", 0, "competencies", 0, "descriptors"], { G: "Clear", R: "Absent" });
    const scaled = withRatingKind(structure, "scale");
    assert.equal(getAt(scaled, ["display", "tones"]), undefined);
    assert.deepEqual(getAt(scaled, ["sections", 0, "competencies", 0, "descriptors"]), {});
    const renamedGrades = withScale(
      setAt(scaled, ["sections", 0, "competencies", 0, "descriptors"], { Good: "Mostly" }),
      ["Excellent", "Solid", "Fair", "Poor"],
    );
    assert.deepEqual(getAt(renamedGrades, ["sections", 0, "competencies", 0, "descriptors"]), { Solid: "Mostly" });
  });

  it("renames the rating field in every domain along with the rating", () => {
    const renamed = withRatingField(appendAt(blankStructure(), ["sections"], newSection(blankStructure(), "domain")), "grade");
    assert.equal(getAt(renamed, ["rating", "field"]), "grade");
    assert.equal(getAt(renamed, ["sections", 0, "competencyFields", 0, "id"]), "grade");
    assert.equal(getAt(renamed, ["sections", 1, "competencyFields", 0, "id"]), "grade");
  });
});

describe("fields", () => {
  it("gives a new field what its type needs", () => {
    assert.deepEqual(newField("singleSelect", []), { id: "choice", label: "Choice", type: "singleSelect", role: "selector", options: ["Option 1"] });
    assert.deepEqual(newField("longText", [{ id: "comment" }]), { id: "comment_2", label: "Comment", type: "longText", role: "explanation" });
  });

  it("changes type, keeping a role the author chose and dropping what no longer applies", () => {
    const select = { id: "verdict", label: "Verdict", type: "singleSelect", role: "selector", options: ["Yes"] };
    assert.deepEqual(withFieldType(select, "longText"), { id: "verdict", label: "Verdict", type: "longText", role: "explanation" });
    const flagged = { id: "concern", label: "Concern", type: "shortText", role: "flag" };
    assert.deepEqual(withFieldType(flagged, "records"), {
      id: "concern",
      label: "Concern",
      type: "records",
      role: "flag",
      fields: [{ id: "detail", label: "Detail", type: "shortText", role: "other" }],
    });
  });
});

describe("problems", () => {
  const problems = [
    { path: "sections[0].competencies[0].id", message: "Ids are lower case." },
    { path: "sections[0].competencyFields", message: "A domain rates each competency in exactly one rating field; this one has 0." },
    { path: "display.tones[0].atLeast", message: "atLeast must be between 0 and 1." },
  ];

  it("pins a problem to its input and counts those inside a card", () => {
    assert.deepEqual(problemsAt(problems, ["sections", 0, "competencies", 0, "id"]), ["Ids are lower case."]);
    assert.equal(problemsWithin(problems, ["sections", 0]), 2);
    assert.equal(problemsWithin(problems, ["sections", 1]), 0);
  });

  it("says where a problem is in the author's words", () => {
    const structure = setAt(blankStructure(), ["sections", 0, "title"], "History");
    assert.equal(placeLabel(structure, "sections[0].competencies[0].id"), "History › Competency 1 › id");
    assert.equal(placeLabel(structure, "display.tones[0].atLeast"), "Results & dashboard › Tone 1 › atLeast");
  });

  it("reads the problems a refused publish carried, and nothing else", () => {
    const details = {
      errors: [
        { path: "rating.scale", message: "A scale rating needs at least one value." },
        { path: 3, message: "not a path" },
        "not an object",
      ],
    };
    assert.deepEqual(problemsFromDetails(details), [{ path: "rating.scale", message: "A scale rating needs at least one value." }]);
    assert.deepEqual(problemsFromDetails({ reason: "other" }), []);
    assert.deepEqual(problemsFromDetails(null), []);
  });
});

describe("draft instructions", () => {
  it("fills only the places with no instructions yet", () => {
    const structure = setAt(blankStructure(), ["sections", 0, "instructions"], "Mine.");
    const { structure: filled, filled: count } = applyInstructionSuggestions(structure, [
      { path: "sections[0]", text: "Suggested domain.", has_instructions: true },
      { path: "sections[0].competencies[0]", text: "Rate how well they did it.", has_instructions: false },
      { path: "sections[0].competencyFields[1]", text: "", has_instructions: false },
    ]);
    assert.equal(count, 1);
    assert.equal(getAt(filled, ["sections", 0, "instructions"]), "Mine.");
    assert.equal(getAt(filled, ["sections", 0, "competencies", 0, "instructions"]), "Rate how well they did it.");
  });
});

describe("preview inputs", () => {
  const rating = { kind: "range", field: "mark", minimum: 0, maximum: 4, step: "integer" };
  const totals = { total: 6, max: 8, fraction: 0.75, passed: true, critical_count: 0, domains: [] };

  it("hands RubricFeedback the normalised draft and the sample result, and nothing while invalid", () => {
    const fed = previewInputs(
      { valid: true, rating, structure: { schemaVersion: 2 }, display: { total: { aggregate: "sum" } }, sample_result: { history: {} }, sample_totals: totals },
      blankStructure(),
    );
    assert.deepEqual(fed?.rubric, { version_id: null, rating, structure: { schemaVersion: 2 }, display: { total: { aggregate: "sum" } } });
    assert.deepEqual(fed?.result.payload, { history: {} });
    assert.equal(fed?.result.totals?.total, 6);
    assert.equal(previewInputs({ valid: false, problems: [] }, blankStructure()), null);
  });

  it("draws a trial mark only once it has marked", () => {
    const preview = { valid: true, rating, structure: { schemaVersion: 2 }, display: {} };
    const marking = { status: "marking" as const, elapsed_seconds: 5, turn_count: 4, rubric_version_id: "v1" };
    assert.equal(trialInputs(marking, preview, blankStructure()), null);
    const marked = { ...marking, status: "marked" as const, marks: { history: { taking: { mark: 3 } } }, totals, model_used: "gpt-test" };
    const fed = trialInputs(marked, preview, blankStructure());
    assert.deepEqual(fed?.result.payload, { history: { taking: { mark: 3 } } });
    assert.equal(fed?.result.model_used, "gpt-test");
  });
});

describe("a fifth exam, authored end to end in the model", () => {
  it("builds a 0-4 station with a written section, a pick-one, records and a summary", () => {
    let exam = withRatingKind(blankStructure(), "range");
    exam = setAt(exam, ["rating", "maximum"], 4);
    exam = withRatingField(exam, "mark");
    exam = setAt(exam, ["sections", 0, "id"], "clinical_reasoning");
    exam = setAt(exam, ["sections", 0, "title"], "Clinical reasoning");
    exam = setAt(exam, ["sections", 0, "competencies", 0], { id: "differentials", label: "Differentials", instructions: "" });
    exam = appendAt(exam, ["sections"], newSection(exam, "section"));
    const writtenFields = ["sections", 1, "fields"] as const;
    exam = appendAt(exam, writtenFields, newField("singleSelect", getAt(exam, writtenFields) as unknown[]));
    exam = setAt(exam, [...writtenFields, 1, "options"], ["Admit", "Discharge"]);
    exam = appendAt(exam, writtenFields, newField("records", getAt(exam, writtenFields) as unknown[]));
    exam = appendAt(exam, ["sections"], newSection(exam, "field"));
    exam = setAt(exam, ["display"], {
      domain: { aggregate: "sum" },
      total: { aggregate: "sum", passAtLeast: 3, requireEveryDomain: false },
      tones: [{ atLeast: 0.75, tone: "good" }, { atLeast: 0, tone: "poor" }],
      labels: { title: "Emergency medicine" },
    });
    exam = applyInstructionSuggestions(exam, [
      { path: "sections[0].competencies[0]", text: "Name three differentials.", has_instructions: false },
      { path: "sections[2].field", text: "One line overall.", has_instructions: false },
    ]).structure;

    assert.deepEqual(exam, {
      schemaVersion: 2,
      rating: { kind: "range", field: "mark", minimum: 0, maximum: 4, step: "integer" },
      sections: [
        {
          id: "clinical_reasoning",
          title: "Clinical reasoning",
          kind: "domain",
          instructions: "",
          competencies: [{ id: "differentials", label: "Differentials", instructions: "Name three differentials." }],
          competencyFields: [
            { id: "mark", type: "rating", role: "rating", label: "Rating" },
            { id: "evidence", type: "longText", role: "evidence", label: "Evidence" },
            { id: "explanation", type: "longText", role: "explanation", label: "Explanation" },
          ],
        },
        {
          id: "section_2",
          title: "Section 2",
          kind: "section",
          instructions: "",
          fields: [
            { id: "notes", label: "Notes", type: "longText", role: "summary" },
            { id: "choice", label: "Choice", type: "singleSelect", role: "selector", options: ["Admit", "Discharge"] },
            {
              id: "entries",
              label: "Entries",
              type: "records",
              role: "other",
              fields: [{ id: "detail", label: "Detail", type: "shortText", role: "other" }],
            },
          ],
        },
        {
          kind: "field",
          title: "Overall comment",
          field: { id: "overall_comment", label: "Overall comment", type: "longText", role: "summary", instructions: "One line overall." },
        },
      ],
      display: {
        domain: { aggregate: "sum" },
        total: { aggregate: "sum", passAtLeast: 3, requireEveryDomain: false },
        tones: [{ atLeast: 0.75, tone: "good" }, { atLeast: 0, tone: "poor" }],
        labels: { title: "Emergency medicine" },
      },
    });
    assert.equal(placeLabel(exam, "sections[1].fields[2].fields[0].id"), "Section 2 › Entries › Detail › id");
  });
});
