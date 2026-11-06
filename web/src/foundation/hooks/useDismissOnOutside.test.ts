import assert from "node:assert/strict";
import { test } from "node:test";
import { dismisses } from "@/foundation/hooks/useDismissOnOutside";

test("a press outside or Escape dismisses; a press inside or another key does not", () => {
  assert.equal(dismisses({ type: "pointerdown", inside: false }), true);
  assert.equal(dismisses({ type: "pointerdown", inside: true }), false);
  assert.equal(dismisses({ type: "keydown", key: "Escape" }), true);
  assert.equal(dismisses({ type: "keydown", key: "Enter" }), false);
});
