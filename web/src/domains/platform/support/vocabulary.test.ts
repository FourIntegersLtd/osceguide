import assert from "node:assert/strict";
import test from "node:test";
import { formatDay, formatSince, isImportedFromOldSite } from "@/domains/platform/support/vocabulary";

const now = new Date("2026-10-06T12:00:00Z");

test("a last sign-in three days ago reads as three days ago, with its date", () => {
  const at = "2026-10-03T09:30:00Z";
  assert.equal(formatSince(at, now), `3 days ago (${formatDay(at)})`);
});

test("days are calendar days: an evening three days back is still three days ago", () => {
  const at = new Date(2026, 9, 3, 20, 0).toISOString();
  assert.equal(formatSince(at, new Date(2026, 9, 6, 8, 0)), `3 days ago (${formatDay(at)})`);
});

test("someone who never signed in reads Never", () => {
  assert.equal(formatSince(null, now), "Never");
});

test("an hour reads in the singular and a fresh sign-in as just now", () => {
  assert.equal(formatSince("2026-10-06T10:59:00Z", now), `1 hour ago (${formatDay("2026-10-06T10:59:00Z")})`);
  assert.equal(formatSince("2026-10-06T11:59:30Z", now), `Just now (${formatDay("2026-10-06T11:59:30Z")})`);
});

test("an attempt marked under legacy-b2c is one imported from the old site", () => {
  assert.equal(isImportedFromOldSite({ result_policy_versions: ["legacy-b2c"] }), true);
  assert.equal(isImportedFromOldSite({ result_policy_versions: ["v3", "legacy-b2c"] }), true);
});

test("an attempt the platform marked itself, or has no result yet, is not imported", () => {
  assert.equal(isImportedFromOldSite({ result_policy_versions: ["v3"] }), false);
  assert.equal(isImportedFromOldSite({ result_policy_versions: [] }), false);
});
