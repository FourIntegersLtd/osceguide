import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { layoutName } from "@/capabilities/authoring/exams/layoutName";

const templates = [
  { title: "History taking", versions: [{ id: "v1" }, { id: "v2" }] },
  { title: "Examination", versions: [{ id: "v3" }] },
];

describe("a station's layout name", () => {
  it("is the title of the template that owns its version", () => {
    assert.equal(layoutName(templates, "v2"), "History taking");
    assert.equal(layoutName(templates, "v3"), "Examination");
  });
  it("is null for a hand-written station or an unknown version", () => {
    assert.equal(layoutName(templates, null), null);
    assert.equal(layoutName(templates, "nope"), null);
  });
});
