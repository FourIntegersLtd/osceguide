import assert from "node:assert/strict";
import test from "node:test";
import { retentionChoiceKey } from "@/domains/assess/settings/retention";

test("retention maps the stored days onto the three choices, anything else is custom", () => {
  assert.equal(retentionChoiceKey(90), "90");
  assert.equal(retentionChoiceKey(null), "null");
  assert.equal(retentionChoiceKey(undefined), "null");
  assert.equal(retentionChoiceKey(200), "custom");
});
