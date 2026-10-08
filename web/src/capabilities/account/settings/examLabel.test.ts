import assert from "node:assert/strict";
import { test } from "node:test";
import { examLabel } from "@/capabilities/account/settings/examLabel";

test("an account with no exam says so instead of inventing one", () => {
  assert.equal(examLabel(null, null), "No exam chosen yet");
});

test("the backend's name wins, then the upper-cased code", () => {
  assert.equal(examLabel("PLAB 2", "plab"), "PLAB 2");
  assert.equal(examLabel(null, "plab"), "PLAB");
});
