import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { sittingHeadPrimary } from "@/domains/assess/sittingWords";

describe("sittingHeadPrimary", () => {
  it("offers Results once the sitting has ended", () => {
    assert.equal(sittingHeadPrimary({ status: "completed", scheduled_for: "2026-11-01T09:00:00Z" }), "results");
  });
  it("offers Set a date when undated", () => {
    assert.equal(sittingHeadPrimary({ status: "scheduled", scheduled_for: null }), "schedule");
  });
  it("otherwise offers Edit", () => {
    assert.equal(sittingHeadPrimary({ status: "scheduled", scheduled_for: "2026-11-01T09:00:00Z" }), "edit");
    assert.equal(sittingHeadPrimary({ status: "in_progress", scheduled_for: "2026-11-01T09:00:00Z" }), "edit");
  });
});
