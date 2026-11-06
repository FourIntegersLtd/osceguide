import assert from "node:assert/strict";
import { test } from "node:test";
import { invitationSubtitle } from "@/capabilities/account/support/invitationCopy";

test("the subtitle names the organisation that invited the person", () => {
  assert.equal(
    invitationSubtitle("Ashford Medical School"),
    "Ashford Medical School has invited you. Choose a password to join.",
  );
});

test("with no organisation the subtitle keeps the current copy", () => {
  assert.equal(invitationSubtitle(null), "Your organisation has invited you. Choose a password to join.");
});
