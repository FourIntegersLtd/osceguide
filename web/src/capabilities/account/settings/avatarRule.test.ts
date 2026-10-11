import assert from "node:assert/strict";
import { test } from "node:test";
import {
  AVATAR_MAX_BYTES,
  avatarButtonLabel,
  avatarTooBig,
} from "@/capabilities/account/settings/avatarRule";

test("the button offers Add photo until there is an avatar, then Change photo", () => {
  assert.equal(avatarButtonLabel(false), "Add photo");
  assert.equal(avatarButtonLabel(true), "Change photo");
});

test("5 MB exactly is accepted and one byte more is refused before upload", () => {
  assert.equal(AVATAR_MAX_BYTES, 5242880);
  assert.equal(avatarTooBig(5242880), false);
  assert.equal(avatarTooBig(5242881), true);
});
