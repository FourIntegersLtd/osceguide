import assert from "node:assert/strict";
import { test } from "node:test";
import { FORCED_PASSWORD_COPY, WRONG_DETAILS_MESSAGE } from "@/capabilities/account/support/signInCopy";

test("a wrong email or password reads as the board's one sentence", () => {
  assert.equal(WRONG_DETAILS_MESSAGE, "That email or password is not right.");
});

test("the forced password change uses the board's labels and button", () => {
  assert.deepEqual(FORCED_PASSWORD_COPY, {
    labels: { currentPassword: "Temporary password", newPassword: "New password", confirmPassword: "Confirm it" },
    submit: "Save password",
  });
});
