import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  resolveGaMeasurementId,
  shouldAskForAnalyticsConsent,
} from "@/foundation/analytics/gaMeasurementId";

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

describe("shouldAskForAnalyticsConsent", () => {
  it("does not ask when there is no measurement id, whatever is stored", () => {
    assert.equal(shouldAskForAnalyticsConsent(null, null), false);
    assert.equal(shouldAskForAnalyticsConsent(null, "accepted"), false);
  });

  it("asks on production when the visitor has not answered yet", () => {
    assert.equal(shouldAskForAnalyticsConsent("G-57RJ52Q20T", null), true);
  });

  it("does not ask once the visitor has accepted or rejected", () => {
    assert.equal(shouldAskForAnalyticsConsent("G-TEST", "accepted"), false);
    assert.equal(shouldAskForAnalyticsConsent("G-TEST", "rejected"), false);
  });
});
