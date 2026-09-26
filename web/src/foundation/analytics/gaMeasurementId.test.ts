import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { resolveGaMeasurementId } from "@/foundation/analytics/gaMeasurementId";

describe("resolveGaMeasurementId", () => {
  it("falls back to production's GA id when nothing is configured and this is production", () => {
    assert.equal(resolveGaMeasurementId(undefined, true), "G-57RJ52Q20T");
  });

  it("loads nothing when nothing is configured and this is not production", () => {
    // Staging and every Vercel preview must never phone production's
    // analytics property — that would mix a developer's or a tester's
    // clicks into real production numbers.
    assert.equal(resolveGaMeasurementId(undefined, false), null);
  });

  it("uses an explicitly configured id even on production", () => {
    assert.equal(resolveGaMeasurementId("G-STAGINGID", true), "G-STAGINGID");
  });

  it("uses an explicitly configured id on a non-production site", () => {
    assert.equal(resolveGaMeasurementId("G-STAGINGID", false), "G-STAGINGID");
  });

  it("loads nothing when the id is explicitly set to an empty string, on production", () => {
    assert.equal(resolveGaMeasurementId("", true), null);
  });

  it("loads nothing when the id is explicitly set to an empty string, off production", () => {
    assert.equal(resolveGaMeasurementId("", false), null);
  });
});
