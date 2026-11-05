import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { authoringTabItems, DEFAULT_AUTHORING_SECTION } from "@/capabilities/authoring/sections";

describe("the Exams hub tabs", () => {
  it("lead with Exams, in the board's order and words", () => {
    assert.deepEqual(
      authoringTabItems(true).map((t) => t.label),
      ["Exams", "Stations", "Marking schemes", "Station layouts", "Programmes"],
    );
    assert.equal(DEFAULT_AUTHORING_SECTION, "exams");
  });
  it("keep every section URL", () => {
    assert.deepEqual(
      authoringTabItems(true).map((t) => t.id),
      ["exams", "stations", "rubrics", "station-templates", "programmes"],
    );
    assert.equal(authoringTabItems(false).some((t) => t.id === "programmes"), false);
  });
});
