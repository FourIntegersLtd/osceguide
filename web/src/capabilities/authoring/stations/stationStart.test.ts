import assert from "node:assert/strict";
import test from "node:test";
import { showsCreateForm, stationStartHref, templatesForChosenExam } from "@/capabilities/authoring/stations/stationStart";

test("a chosen way carries the exam to the form", () => {
  assert.equal(
    stationStartHref("/app/x/authoring/stations/new", "ai", "finals"),
    "/app/x/authoring/stations/new?start=ai&exam=finals",
  );
  assert.equal(stationStartHref("/n", "blank", ""), "/n?start=blank");
});

test("the form shows after a choice or when a template is named, the chooser otherwise", () => {
  const params = (q: string) => new URLSearchParams(q);
  assert.equal(showsCreateForm(params(""), "org"), false);
  assert.equal(showsCreateForm(params("start=layout"), "org"), true);
  assert.equal(showsCreateForm(params("templateVersion=abc"), "org"), true);
});

test("the staff console never sees the chooser", () => {
  assert.equal(showsCreateForm(new URLSearchParams(""), "platform"), true);
});

test("an exam from the chooser narrows the templates; a named template is never narrowed", () => {
  const all = [
    { id: "a", exam_code: "finals" },
    { id: "b", exam_code: "other" },
    { id: "c", exam_code: null },
  ];
  const ids = (q: string) => templatesForChosenExam(all, new URLSearchParams(q)).map((t) => t.id);
  assert.deepEqual(ids("exam=finals"), ["a", "c"]);
  assert.deepEqual(ids(""), ["a", "b", "c"]);
  assert.deepEqual(ids("exam=finals&templateVersion=v1"), ["a", "b", "c"]);
});
