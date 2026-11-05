import assert from "node:assert/strict";
import test from "node:test";
import { STATION_START_WAYS, showsCreateForm, stationStartHref } from "@/capabilities/authoring/stations/stationStart";

test("the chooser offers five ways, in the board's order", () => {
  assert.deepEqual(
    STATION_START_WAYS.map((w) => w.title),
    [
      "From a layout",
      "Import a PDF or Word file",
      "Draft with AI from a brief",
      "Copy from the library",
      "Start blank",
    ],
  );
  assert.equal(STATION_START_WAYS[4]?.cta, "Open the builder");
});

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
