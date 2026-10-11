import assert from "node:assert/strict";
import { test } from "node:test";
import { JUMP_GAP, jumpScrollTop, stuckBottom } from "@/capabilities/media/jumpGeometry";

test("a jump lands the heading just under the sticky header, never above the page", () => {
  assert.equal(jumpScrollTop(900, 100, 140), 1000 - 140 - JUMP_GAP);
  assert.equal(jumpScrollTop(10, 0, 140), 0);
});

test("the header is measured where it sticks, not where it rests under the page title", () => {
  // Inner scroller 64px down the viewport, header pinned at top: 0 and 155px tall: it sticks at 219,
  // whatever its bottom was at rest (455 before the page scrolled).
  assert.equal(stuckBottom(64, 0, 155), 219);
  // A window scroller (top above the viewport once scrolled) pins the header to the viewport top.
  assert.equal(stuckBottom(-800, 8, 155), 163);
});
