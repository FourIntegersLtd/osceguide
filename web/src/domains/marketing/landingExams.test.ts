import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildExamUrl } from "@/domains/marketing/landingExams";

describe("buildExamUrl", () => {
  it("builds production subdomain URLs", () => {
    assert.equal(
      buildExamUrl("sca", "osceguide.com", "", "https:"),
      "https://sca.osceguide.com",
    );
    assert.equal(
      buildExamUrl("plab", "www.osceguide.com", "", "https:"),
      "https://plab.osceguide.com",
    );
  });

  it("builds local lvh.me URLs with port", () => {
    assert.equal(
      buildExamUrl("ortho", "lvh.me", "3000", "http:"),
      "http://ortho.lvh.me:3000",
    );
  });

  it("defaults local port to 3000 when omitted", () => {
    assert.equal(
      buildExamUrl("sca", "127.0.0.1", "", "http:"),
      "http://sca.lvh.me:3000",
    );
  });

  it("REGRESSION: builds the staging subdomain on staging, never production's", () => {
    // A click from staging.osceguide.com must land on the exam's staging
    // subdomain, not silently send the visitor to production.
    assert.equal(
      buildExamUrl("sca", "staging.osceguide.com", "", "https:", "staging.osceguide.com"),
      "https://sca.staging.osceguide.com",
    );
  });
});
