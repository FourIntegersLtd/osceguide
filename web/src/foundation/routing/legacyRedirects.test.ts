import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  CONSUMER_REDIRECTS,
  PREFIX_REDIRECTS,
  legacyDestination as destination,
  legacyDestination,
} from "@/foundation/routing/legacyRedirects";

describe("legacy redirects", () => {
  it("moves the old consumer root paths under the personal workspace", () => {
    assert.equal(destination("/dashboard"), "/app/me/dashboard");
    assert.equal(destination("/mocks"), "/app/me/mocks");
    assert.equal(destination("/library"), "/app/me/library");
  });

  it("keeps both spellings of the dashboard alive", () => {
    // The first cut of platform-web called it "practice"; the old client
    // called it "dashboard". Neither should 404.
    assert.equal(destination("/practice"), "/app/me/dashboard");
    assert.equal(destination("/dashboard"), "/app/me/dashboard");
  });

  it("carries a sub-path across with the rest of the URL intact", () => {
    assert.equal(destination("/mocks/abc-123/stations/s1"), "/app/me/mocks/abc-123/stations/s1");
    assert.equal(destination("/b2b/kings/sessions/s1/circuits/c1"), "/app/kings/sessions/s1/circuits/c1");
  });

  it("reads the staff console before it reads an organisation", () => {
    // `/b2b/platform` must never be understood as an org called "platform".
    assert.equal(destination("/b2b/platform"), "/staff");
    assert.equal(destination("/b2b/platform/organizations"), "/staff/organizations");
    assert.equal(destination("/platform/users"), "/staff/users");
  });

  it("drops the arm prefix from every old workspace URL", () => {
    assert.equal(destination("/b2b/kings/dashboard"), "/app/kings/dashboard");
    assert.equal(destination("/b2b/partner/bmj/exams"), "/app/bmj/exams");
    assert.equal(destination("/b2b/practice/kings/history"), "/app/kings/history");
    assert.equal(destination("/assess/kings/sittings"), "/app/kings/sittings");
    assert.equal(destination("/hire/acme/sittings"), "/app/acme/sittings");
  });

  it("leaves a current address alone", () => {
    assert.equal(destination("/app/me/dashboard"), null);
    assert.equal(destination("/login"), null);
    assert.equal(destination("/"), null);
    assert.equal(destination("/exams/sca"), null);
  });

  it("never answers with the path it was given", () => {
    // A row that maps a path to itself would loop the browser forever. This is
    // the property that makes the table safe to extend without reading it all.
    const samples = [
      ...CONSUMER_REDIRECTS.map((r) => r.from),
      "/b2b/kings/sessions",
      "/b2b/platform/audit",
      "/assess/kings",
      "/hire/acme",
      "/platform",
      "/app/me/dashboard",
      "/app/kings/sessions",
      "/staff/users",
      "/",
    ];
    for (const path of samples) {
      const to = legacyDestination(path);
      assert.notEqual(to, path, `${path} redirects to itself`);
    }
  });

  it("settles after one hop", () => {
    // Following a redirect must never produce another one, or the browser
    // gives up with ERR_TOO_MANY_REDIRECTS and the page is simply gone.
    for (const { from } of CONSUMER_REDIRECTS) {
      const once = legacyDestination(from);
      assert.ok(once, `${from} should redirect`);
      assert.equal(legacyDestination(once), null, `${from} → ${once} → redirects again`);
    }
    for (const sample of ["/b2b/kings/sessions", "/b2b/platform/users", "/assess/kings", "/hire/acme"]) {
      const once = legacyDestination(sample);
      assert.ok(once);
      assert.equal(legacyDestination(once), null, `${sample} → ${once} → redirects again`);
    }
  });

  it("has no duplicate rows", () => {
    const froms = CONSUMER_REDIRECTS.map((r) => r.from);
    assert.equal(new Set(froms).size, froms.length);
    const patterns = PREFIX_REDIRECTS.map((r) => r.pattern.source);
    assert.equal(new Set(patterns).size, patterns.length);
  });
});
