import assert from "node:assert/strict";
import test from "node:test";
import { showsCreateForm, stationStartHref } from "@/capabilities/authoring/stations/stationStart";

test("a chosen way carries the exam to the form", () => {
  assert.equal(
    stationStartHref("/app/x/authoring/stations/new", "ai", "finals"),
    "/app/x/authoring/stations/new?start=ai&exam=finals",
  );
  assert.equal(stationStartHref("/n", "blank", ""), "/n?start=blank");
});

test("the form shows after a choice or when a template is named, the chooser otherwise", () => {
  const params = (q: string) => new URLSearchParams(q);
  assert.equal(showsCreateForm(params("")), false);
  assert.equal(showsCreateForm(params("start=layout")), true);
  assert.equal(showsCreateForm(params("templateVersion=abc")), true);
});
