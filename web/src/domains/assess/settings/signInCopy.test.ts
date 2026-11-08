import assert from "node:assert/strict";
import { test } from "node:test";
import { assessWordsFor } from "@/capabilities/assess-words/vocabulary";
import { mfaPills, ssoLead, staffMfaCopy } from "@/domains/assess/settings/signInCopy";

test("an institution keeps its staff two-step wording", () => {
  assert.deepEqual(staffMfaCopy(true, assessWordsFor("assess")), {
    title: "Two-step sign-in for staff",
    detail: "Staff must confirm a code as well as a password.",
  });
  assert.equal(staffMfaCopy(false, assessWordsFor("assess")).detail, "Staff sign in with a password alone.");
});

test("an employer names administrators and assessors", () => {
  assert.deepEqual(staffMfaCopy(true, assessWordsFor("hire")), {
    title: "Two-step sign-in",
    detail: "Administrators and assessors must also enter a code from their phone when they sign in.",
  });
  assert.equal(
    staffMfaCopy(false, assessWordsFor("hire")).detail,
    "Administrators and assessors sign in with a password alone.",
  );
});

test("the two-step pills mark the current policy", () => {
  assert.deepEqual(mfaPills(true), [
    { label: "Optional", on: false },
    { label: "Required for administrators and assessors", on: true },
  ]);
  assert.equal(mfaPills(false)[0]?.on, true);
});

test("the Single sign-on lead pins both literals", () => {
  assert.equal(ssoLead(assessWordsFor("assess")), "OSCE Guide sets this up with you. Contact support to change it.");
  assert.equal(ssoLead(assessWordsFor("hire")), "Staff sign in with their work account when single sign-on is connected. Candidates still sign in with email.");
});
