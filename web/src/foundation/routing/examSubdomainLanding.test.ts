import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { getExamFromHost } from "@/foundation/routing/examFromHost";
import { examLandingRewritePath } from "@/foundation/routing/examSubdomainLanding";

describe("getExamFromHost", () => {
  it("reads exam subdomains on lvh.me", () => {
    assert.equal(getExamFromHost("sca.lvh.me:3000"), "sca");
    assert.equal(getExamFromHost("plab.lvh.me"), "plab");
  });

  it("reads exam subdomains on osceguide.com via alternate base", () => {
    assert.equal(getExamFromHost("sca.osceguide.com"), "sca");
  });

  it("returns null for apex host", () => {
    assert.equal(getExamFromHost("lvh.me:3000"), null);
    assert.equal(getExamFromHost("www.lvh.me"), null);
  });
});

describe("examLandingRewritePath", () => {
  it("rewrites supported exam subdomain roots", () => {
    assert.equal(examLandingRewritePath("sca.lvh.me:3000", "/"), "/exams/sca");
    assert.equal(examLandingRewritePath("sca.lvh.me:3000", ""), "/exams/sca");
  });

  it("does not rewrite nested paths", () => {
    assert.equal(examLandingRewritePath("sca.lvh.me:3000", "/login"), null);
  });

  it("ignores unknown subdomains", () => {
    assert.equal(examLandingRewritePath("avodeck.lvh.me:3000", "/"), null);
  });
});
