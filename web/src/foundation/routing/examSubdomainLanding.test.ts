import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { examFromHostAndSite, getExamFromHost } from "@/foundation/routing/examFromHost";
import { examLandingRewritePath } from "@/foundation/routing/examSubdomainLanding";

describe("getExamFromHost", () => {
  it("reads exam subdomains on lvh.me", () => {
    assert.equal(getExamFromHost("sca.lvh.me:3000"), "sca");
    assert.equal(getExamFromHost("plab.lvh.me"), "plab");
  });

  it("reads exam subdomains on production, the default site when NEXT_PUBLIC_SITE_URL is unset", () => {
    assert.equal(getExamFromHost("sca.osceguide.com"), "sca");
  });

  it("returns null for apex host", () => {
    assert.equal(getExamFromHost("lvh.me:3000"), null);
    assert.equal(getExamFromHost("www.lvh.me"), null);
  });
});

/**
 * `examFromHostAndSite` is the pure resolver: it takes the site's own
 * hostname as a literal argument, so every deployment shape can be asserted
 * without mutating `process.env` — see `foundation/config/siteUrl.ts` for why
 * `NODE_ENV` cannot stand in for "which site is this".
 */
describe("examFromHostAndSite", () => {
  it("resolves an exam subdomain in production", () => {
    assert.equal(examFromHostAndSite("sca.osceguide.com", "osceguide.com"), "sca");
  });

  it("resolves an exam subdomain on staging, relative to the staging host", () => {
    assert.equal(
      examFromHostAndSite("sca.staging.osceguide.com", "staging.osceguide.com"),
      "sca",
    );
  });

  it("REGRESSION: does not read the bare staging host as an exam called 'staging'", () => {
    // This is the real bug: staging's site host has its own subdomain
    // (`staging.osceguide.com`), and a naive "strip the last two labels"
    // reading would treat "staging" as the exam. It must not — the bare
    // staging host names no exam, exactly like the bare production host.
    assert.equal(examFromHostAndSite("staging.osceguide.com", "staging.osceguide.com"), null);
  });

  it("does not resolve a production exam host as an exam on a staging deployment", () => {
    // `sca.osceguide.com` does not end with `staging.osceguide.com`, so a
    // staging deployment must not mistake a production URL for its own.
    assert.equal(examFromHostAndSite("sca.osceguide.com", "staging.osceguide.com"), null);
  });

  it("returns null for localhost", () => {
    assert.equal(examFromHostAndSite("localhost:3000", "osceguide.com"), null);
  });

  it("returns null for a Vercel preview host, which is never an exam subdomain", () => {
    assert.equal(examFromHostAndSite("my-branch-osce.vercel.app", "osceguide.com"), null);
  });

  it("still resolves local dev's lvh.me subdomains, whichever site is configured", () => {
    assert.equal(examFromHostAndSite("sca.lvh.me:3000", "staging.osceguide.com"), "sca");
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
