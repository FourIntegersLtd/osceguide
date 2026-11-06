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
      "Version 3, published 2 Oct. 2 domains, rated Good, Fair or Poor.",
    );
  });
  it("reads a version 3 scheme: domains from the outline, labels from the first scale", () => {
    const structure = {
      schemaVersion: 3,
      scales: [{ id: "rag", name: "RAG", levels: [{ value: "R", label: "Red", points: 0 }, { value: "A", label: "Amber", points: 1 }, { value: "G", label: "Green", points: 2 }] }],
      outline: [{ block: "domain", id: "d1" }, { block: "notes", id: "n1" }],
    };
    assert.equal(schemeLine({ version: 1, published_at: null, structure }), "Version 1, not published. 1 domain, rated Red, Amber or Green.");
  });
  it("reads a number scale as a range", () => {
    const structure = { schemaVersion: 3, scales: [{ id: "n", name: "N", from: 0, to: 10, step: "whole" }], outline: [{ block: "domain", id: "d1" }] };
    assert.equal(schemeLine({ version: 2, published_at: null, structure }), "Version 2, not published. 1 domain, rated 0 to 10.");
  });
  it("says so when a version is not published", () => {
    assert.equal(schemeLine({ version: 1, published_at: null, structure: {} }), "Version 1, not published.");
  });
});
