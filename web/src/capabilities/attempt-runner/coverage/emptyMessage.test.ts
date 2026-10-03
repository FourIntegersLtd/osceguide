import assert from "node:assert/strict";
import { test } from "node:test";
import { coverageEmptyMessage } from "./emptyMessage";

test("before the patient joins, an unfrozen rubric is not reported as unsupported", () => {
  assert.equal(
    coverageEmptyMessage({ supported: false, isLive: true, supportKnown: false }),
    "Listening. Things you cover will appear here as you go.",
  );
});

test("once the patient has joined, a rubric with no live domains says so", () => {
  assert.equal(
    coverageEmptyMessage({ supported: false, isLive: true, supportKnown: true }),
    "Live marking isn't available for this station. Your feedback comes at the end.",
  );
  assert.equal(
    coverageEmptyMessage({ supported: true, isLive: false, supportKnown: true }),
    "Your consultation will be marked here as it happens.",
  );
});
