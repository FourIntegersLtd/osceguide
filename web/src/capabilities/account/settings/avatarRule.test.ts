import assert from "node:assert/strict";
import { test } from "node:test";
import {
  AVATAR_CAPTION,
  AVATAR_MAX_BYTES,
  AVATAR_TOO_BIG,
} from "@/capabilities/account/settings/avatarRule";

test("the limit is 5 MB in bytes and the caption and refusal quote the same number", () => {
  assert.equal(AVATAR_MAX_BYTES, 5242880);
  assert.equal(AVATAR_CAPTION, "JPG or PNG, 5 MB max");
  assert.equal(AVATAR_TOO_BIG, "That photo is over 5 MB. Choose a smaller JPG or PNG.");
});
