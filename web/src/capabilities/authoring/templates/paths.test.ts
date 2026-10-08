import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { stationTemplateNewPath } from "@/capabilities/authoring/templates/paths";
import { stationNewPath } from "@/capabilities/authoring/stations/paths";

const hrefFor = (path: string) => `/org/kings${path}`;

describe("stationTemplateNewPath", () => {
  it("carries the exam so the wizard does not ask for it again", () => {
    assert.equal(
      stationTemplateNewPath(hrefFor, "my exam"),
      "/org/kings/authoring/station-templates/new?exam=my%20exam",
    );
  });

  it("is the bare wizard without an exam", () => {
    assert.equal(stationTemplateNewPath(hrefFor), "/org/kings/authoring/station-templates/new");
  });
});

describe("template to station round trip", () => {
  it("asks the wizard to return to station creation", () => {
    assert.equal(
      stationTemplateNewPath(hrefFor, "my exam", { thenStation: true }),
      "/org/kings/authoring/station-templates/new?exam=my%20exam&then=station",
    );
  });

  it("opens station creation with the new template version selected", () => {
    assert.equal(
      stationNewPath(hrefFor, "ver-1"),
      "/org/kings/authoring/stations/new?templateVersion=ver-1",
    );
    assert.equal(stationNewPath(hrefFor), "/org/kings/authoring/stations/new");
  });
});
