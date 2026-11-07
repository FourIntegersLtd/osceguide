import assert from "node:assert/strict";
import test from "node:test";
import {
  appealIsLive,
  appealStatusLabel,
  erasureConfirmed,
  retentionChoiceKey,
  secondMarkerChoices,
} from "@/domains/assess/results/appealsView";

const members = [
  { user_id: "a", email: "signer@x.org", role: "institution_admin" },
  { user_id: "b", email: "second@x.org", role: "owner" },
  { user_id: "c", email: "gone@x.org", role: "admin", revoked_at: "2026-01-01" },
  { user_id: "d", email: "sup@x.org", role: "supervisor" },
];

test("the second marker is a live administrator other than the one who signed off", () => {
  const choices = secondMarkerChoices(members, { original_marker_ids: ["a"] });
  assert.deepEqual(choices, [{ userId: "b", label: "second@x.org" }]);
});

test("statuses read in words and only open or in review count as waiting", () => {
  assert.equal(appealStatusLabel("in_review"), "With the second marker");
  assert.equal(appealIsLive({ status: "open" }), true);
  assert.equal(appealIsLive({ status: "declined" }), false);
});

test("retention maps the stored days onto the three choices, anything else is custom", () => {
  assert.equal(retentionChoiceKey(90), "90");
  assert.equal(retentionChoiceKey(null), "null");
  assert.equal(retentionChoiceKey(undefined), "null");
  assert.equal(retentionChoiceKey(200), "custom");
});

test("erasure is confirmed only by the candidate's own address, ignoring case and padding", () => {
  assert.equal(erasureConfirmed(" Tess@X.org ", "tess@x.org"), true);
  assert.equal(erasureConfirmed("tess", "tess@x.org"), false);
  assert.equal(erasureConfirmed("anything", null), false);
});
