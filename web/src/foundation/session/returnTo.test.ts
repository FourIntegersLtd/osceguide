import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { isPublicPath, sanitizeReturnTo } from "@/foundation/session/returnTo";

describe("return-to sanitising", () => {
  it("keeps a same-origin path", () => {
    assert.equal(sanitizeReturnTo("/app/me/mocks"), "/app/me/mocks");
    assert.equal(sanitizeReturnTo("/app/kings/sittings?page=2"), "/app/kings/sittings?page=2");
  });

  it("refuses another origin", () => {
    // `//evil.example` is protocol-relative: browsers treat it as a different
    // site, so a leading-slash check alone is an open redirect — on the one
    // page where an open redirect is worth the most.
    assert.equal(sanitizeReturnTo("//evil.example/app"), null);
    assert.equal(sanitizeReturnTo("https://evil.example"), null);
    assert.equal(sanitizeReturnTo("javascript:alert(1)"), null);
  });

  it("refuses a page that needs no session", () => {
    // Returning somebody to the sign-in page they just left is a loop.
    assert.equal(sanitizeReturnTo("/login"), null);
    assert.equal(sanitizeReturnTo("/"), null);
    assert.equal(sanitizeReturnTo("/exams/sca"), null);
  });

  it("refuses nothing at all", () => {
    assert.equal(sanitizeReturnTo(null), null);
    assert.equal(sanitizeReturnTo(""), null);
  });

  it("knows the public paths from the private ones", () => {
    assert.ok(isPublicPath("/compliances/privacy-policy"));
    assert.ok(!isPublicPath("/app/me/dashboard"));
  });
});
