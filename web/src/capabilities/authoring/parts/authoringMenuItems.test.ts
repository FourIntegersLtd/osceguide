import assert from "node:assert/strict";
import test from "node:test";
import { visibleMenuItems } from "./authoringMenuItems";

const items = [
  { label: "Open", href: "/x" },
  { label: "Publish", write: true },
  { label: "Delete", write: true, tone: "danger" as const },
];

test("a reader keeps only the items that are not writes", () => {
  assert.deepEqual(visibleMenuItems(items, false).map((i) => i.label), ["Open"]);
});

test("an author keeps every item and the write flag is not passed on", () => {
  const shown = visibleMenuItems(items, true);
  assert.deepEqual(shown.map((i) => i.label), ["Open", "Publish", "Delete"]);
  assert.equal("write" in (shown[1] ?? {}), false);
});

test("items that are false or null are skipped", () => {
  assert.deepEqual(visibleMenuItems([false, null, { label: "A" }], true).map((i) => i.label), ["A"]);
});
