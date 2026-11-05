import assert from "node:assert/strict";
import test from "node:test";
import { navBadgeGate, navBadges } from "@/surfaces/navBadges";

test("chips are only for assess and hire, and only to people who run circuits", () => {
  assert.deepEqual(navBadgeGate("assess", true, true), { live: true, results: true });
  assert.deepEqual(navBadgeGate("hire", true, false), { live: true, results: false });
  assert.deepEqual(navBadgeGate("assess", false, true), { live: false, results: false });
  assert.deepEqual(navBadgeGate("train", true, true), { live: false, results: false });
});

test("a zero or unread count shows no chip", () => {
  assert.deepEqual(navBadges(2, 5), { live: "2 live", results: "5" });
  assert.deepEqual(navBadges(0, 0), { live: undefined, results: undefined });
  assert.deepEqual(navBadges(null, null), { live: undefined, results: undefined });
});
