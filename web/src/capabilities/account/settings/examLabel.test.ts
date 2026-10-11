import assert from "node:assert/strict";
import { test } from "node:test";
import { examLabel } from "@/capabilities/account/settings/examLabel";

test("an account with no exam has no label, so no exam is invented", () => {
  assert.equal(examLabel(null, null), null);
});

test("the backend's name wins, then the upper-cased code", () => {
  assert.equal(examLabel("PLAB 2", "plab"), "PLAB 2");
  assert.equal(examLabel(null, "plab"), "PLAB");
});

test("an empty code is no exam", () => {
  assert.equal(examLabel(null, ""), null);
});

test("a name whose initials are the code reads as name and code", () => {
  assert.equal(examLabel("Simulated Consultation Assessment", "sca"), "Simulated Consultation Assessment (SCA)");
});
