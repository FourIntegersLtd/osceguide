import assert from "node:assert/strict";
import { it } from "node:test";
import { examAuthHref, normalizeExamCode, readExamSelection, rememberExamSelection, rememberLandingExam } from "./examSelection";
it("preserves each exam across login and registration links", () => {
  for (const exam of ["sca", "plab", "casc", "ortho"]) {
    assert.equal(examAuthHref("/login", exam), `/login?appType=${exam}`);
    assert.equal(examAuthHref("/register", exam), `/register?appType=${exam}`);
  }
  assert.equal(normalizeExamCode("SCA"), "sca");
  assert.equal(examAuthHref("/login", "invalid"), "/login");
});

it("a login link's appType seeds the exam for a person with none, and never overwrites a chosen one", () => {
  const store = new Map<string, string>();
  const g = globalThis as unknown as Record<string, unknown>;
  g.localStorage = {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => void store.set(key, value),
  };
  g.window = { dispatchEvent: () => true };
  rememberLandingExam("u1", "sca");
  assert.equal(readExamSelection("u1"), "sca");
  rememberLandingExam("u1", "plab");
  assert.equal(readExamSelection("u1"), "sca");
  rememberExamSelection("u1", "plab");
  assert.equal(readExamSelection("u1"), "plab");
});
