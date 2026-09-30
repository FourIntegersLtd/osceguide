import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { SITE_URL, isProductionSiteUrl, siteHostname } from "@/foundation/config/siteUrl";

describe("SITE_URL", () => {
  it("defaults to production's own origin when NEXT_PUBLIC_SITE_URL is unset", () => {
    // The test runner starts with no NEXT_PUBLIC_SITE_URL, so the module's
    // module-load-time default is exercised here.
    assert.equal(SITE_URL, "https://osceguide.com");
  });
});

describe("isProductionSiteUrl", () => {
  it("is true only for production's exact origin", () => {
    assert.equal(isProductionSiteUrl("https://osceguide.com"), true);
  });

  it("is false for staging", () => {
    assert.equal(isProductionSiteUrl("https://staging.osceguide.com"), false);
  });

  it("is false for a Vercel preview", () => {
    assert.equal(isProductionSiteUrl("https://my-branch-osce.vercel.app"), false);
  });

  it("is false for production with a trailing slash — SITE_URL is normalised, so this must not match", () => {
    assert.equal(isProductionSiteUrl("https://osceguide.com/"), false);
  });
});

describe("siteHostname", () => {
  it("reads the hostname off a site URL", () => {
    assert.equal(siteHostname("https://osceguide.com"), "osceguide.com");
    assert.equal(siteHostname("https://staging.osceguide.com"), "staging.osceguide.com");
  });

  it("falls back to production's hostname for a malformed URL", () => {
    assert.equal(siteHostname("not-a-url"), "osceguide.com");
  });
});
