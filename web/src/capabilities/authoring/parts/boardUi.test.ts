import assert from "node:assert/strict";
import { test } from "node:test";
import { statusChip } from "@/capabilities/authoring/parts/boardTokens";
import { boardBtn } from "@/foundation/ui/boardKit";

test("statusChip words and tones follow the board", () => {
  assert.deepEqual(statusChip("published"), { tone: "ok", label: "● Published" });
  assert.deepEqual(statusChip("active"), { tone: "ok", label: "● Active" });
  assert.deepEqual(statusChip("retired"), { tone: "neutral", label: "● Retired" });
  assert.deepEqual(statusChip("archived"), { tone: "neutral", label: "● Archived" });
  assert.deepEqual(statusChip("draft"), { tone: "warn", label: "● Draft" });
  assert.deepEqual(statusChip(undefined), { tone: "warn", label: "● Draft" });
});

test("boardBtn is 44px, or 36px when small", () => {
  assert.match(boardBtn(), /min-h-11/);
  assert.match(boardBtn("primary", true), /min-h-9/);
  assert.doesNotMatch(boardBtn("primary", true), /min-h-11/);
});
