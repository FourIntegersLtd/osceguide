import assert from "node:assert/strict";
import { it } from "node:test";
import { examAuthHref, normalizeExamCode, resolveCurrentExam } from "./examSelection";

it("preserves each exam across login and registration links", () => {
  for (const exam of ["sca", "plab", "casc", "ortho"]) {
    assert.equal(examAuthHref("/login", exam), `/login?appType=${exam}`);
    assert.equal(examAuthHref("/register", exam), `/register?appType=${exam}`);
  }
  assert.equal(normalizeExamCode("SCA"), "sca");
  assert.equal(examAuthHref("/login", "invalid"), "/login");
});

it("the server's answer is the exam shown, whatever the account's sign-up exam says", () => {
  assert.equal(resolveCurrentExam({ serverCurrent: "sca", accountExam: "plab", codes: ["sca", "plab"] }), "sca");
});

it("falls back to the account's exam, then the first one they may open, then none", () => {
  assert.equal(resolveCurrentExam({ serverCurrent: null, accountExam: "plab", codes: [] }), "plab");
  assert.equal(resolveCurrentExam({ serverCurrent: null, accountExam: null, codes: ["casc"] }), "casc");
  assert.equal(resolveCurrentExam({ serverCurrent: null, accountExam: null, codes: [] }), null);
});
