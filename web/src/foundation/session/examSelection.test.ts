import assert from "node:assert/strict";
import { it } from "node:test";
import { examAuthHref, normalizeExamCode } from "./examSelection";
it("preserves each exam across login and registration links", () => {
  for (const exam of ["sca", "plab", "casc", "ortho"]) {
    assert.equal(examAuthHref("/login", exam), `/login?appType=${exam}`);
    assert.equal(examAuthHref("/register", exam), `/register?appType=${exam}`);
  }
  assert.equal(normalizeExamCode("SCA"), "sca");
  assert.equal(examAuthHref("/login", "invalid"), "/login");
});
