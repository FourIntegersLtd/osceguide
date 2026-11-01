import assert from "node:assert/strict";
import { it } from "node:test";
import { classifyExam, examAuthHref, normalizeExamCode, resolveCurrentExam } from "./examCode";

it("preserves each exam across login and registration links", () => {
  for (const exam of ["sca", "plab", "casc", "ortho"]) {
    assert.equal(examAuthHref("/login", exam), `/login?appType=${exam}`);
    assert.equal(examAuthHref("/register", exam), `/register?appType=${exam}`);
  }
  assert.equal(normalizeExamCode("SCA"), "sca");
  assert.equal(examAuthHref("/login", "invalid"), "/login");
});

it("the server's answer is the exam shown, whatever else the person holds", () => {
  assert.equal(resolveCurrentExam({ serverCurrent: "sca", codes: ["plab", "sca"] }), "sca");
});

it("no answer from the server is no exam, never the account's sign-up exam", () => {
  // Loading, failed, or fail-closed on a retired sign-up exam: all arrive as this. This test is
  // the only guard of that rule (the TRAIN-12 journey does not reach it: the api answers there).
  assert.equal(resolveCurrentExam({ serverCurrent: null, codes: [] }), null);
});

it("a response that lists exams but names none as current opens the first listed", () => {
  assert.equal(resolveCurrentExam({ serverCurrent: null, codes: ["casc", "sca"] }), "casc");
});

it("is ready with the code the app names, even while a reload is in flight", () => {
  assert.deepEqual(classifyExam({ code: "sca", loading: false, error: null }), { kind: "ready", code: "sca" });
  assert.deepEqual(classifyExam({ code: "sca", loading: true, error: null }), { kind: "ready", code: "sca" });
});

it("waits while the dashboard loads", () => {
  assert.deepEqual(classifyExam({ code: null, loading: true, error: null }), { kind: "loading" });
});

it("is unknown, and says it failed, once the dashboard failed", () => {
  assert.deepEqual(classifyExam({ code: null, loading: false, error: new Error("502") }), { kind: "unknown", failed: true });
});

it("is unknown when the api names no exam, and never carries a code", () => {
  const state = classifyExam({ code: null, loading: false, error: null });
  assert.deepEqual(state, { kind: "unknown", failed: false });
  assert.ok(!("code" in state));
});
