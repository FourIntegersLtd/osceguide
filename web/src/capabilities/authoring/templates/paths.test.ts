import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { stationTemplateNewPath } from "@/capabilities/authoring/templates/paths";

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
