import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { schemeLine } from "@/capabilities/authoring/exams/schemeLine";

describe("schemeLine", () => {
  it("reads version, publish day, areas and the rating scale", () => {
    const structure = {
      rating: { kind: "scale", scale: ["Good", "Fair", "Poor"] },
      sections: [{ kind: "domain" }, { kind: "domain" }, { kind: "field" }],
    };
    assert.equal(
      schemeLine({ version: 3, published_at: "2026-10-02T09:00:00Z", structure }),
      "Version 3, published 2 Oct. 2 areas, rated Good, Fair or Poor.",
    );
  });
  it("says so when a version is not published", () => {
    assert.equal(schemeLine({ version: 1, published_at: null, structure: {} }), "Version 1, not published.");
  });
});
