import assert from "node:assert/strict";
import { test } from "node:test";
import { menuFocusTarget } from "@/foundation/ui/popupMenuKeys";

const disabled = [true, false, true, false, false, true];

test("Home and End land on the first and last enabled item", () => {
  assert.equal(menuFocusTarget(disabled, 3, "Home"), 1);
  assert.equal(menuFocusTarget(disabled, 1, "End"), 4);
});

test("arrows step over disabled items and wrap", () => {
  assert.equal(menuFocusTarget(disabled, 1, "ArrowDown"), 3);
  assert.equal(menuFocusTarget(disabled, 4, "ArrowDown"), 1);
  assert.equal(menuFocusTarget(disabled, 1, "ArrowUp"), 4);
  assert.equal(menuFocusTarget(disabled, -1, "ArrowDown"), 1);
  assert.equal(menuFocusTarget(disabled, 3, "a"), null);
  assert.equal(menuFocusTarget([true, true], -1, "Home"), null);
});
