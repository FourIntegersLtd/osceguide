import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { PlatformError, PlatformTransportError } from "@/foundation/platform-client";
import { mapResetPasswordError } from "@/capabilities/account/support/mapAuthApiError";

const refused = (status: number, code: PlatformError["code"], message: string) =>
  new PlatformError(status, { code, message, details: null, request_id: null });

describe("a refused set-password", () => {
  it("says a spent or expired link is no longer valid", () => {
    const result = mapResetPasswordError(refused(422, "invalid_reset_token", "expired"), false);
    assert.deepEqual(result, {
      formError: "That link is no longer valid. Ask for a new one and use the most recent email.",
      fieldErrors: {},
      linkSpent: true,
    });
  });

  it("tells an invited person who already chose a password to sign in", () => {
    const result = mapResetPasswordError(refused(422, "invalid_reset_token", "expired"), true);
    assert.equal(
      result.formError,
      "That invitation has already been used or has expired. If you already chose a password, sign in. Otherwise ask the person who invited you to send it again.",
    );
    assert.equal(result.linkSpent, true);
  });

  it("puts a weak password on the password field, not on the link", () => {
    const result = mapResetPasswordError(
      refused(422, "weak_password", "Mix letters with numbers, punctuation, or capitals"),
      false,
    );
    assert.deepEqual(result, {
      formError: null,
      fieldErrors: { password: "Mix letters with numbers, punctuation, or capitals" },
      linkSpent: false,
    });
  });

  it("asks somebody rate limited to wait, with the link still good", () => {
    const result = mapResetPasswordError(
      refused(429, "too_many_requests", "Too many attempts. Wait a moment and try again."),
      true,
    );
    assert.deepEqual(result, {
      formError: "Too many attempts. Wait a moment and try again.",
      fieldErrors: {},
      linkSpent: false,
    });
  });

  it("calls a request that never arrived a failure to save, not a dead link", () => {
    const result = mapResetPasswordError(new PlatformTransportError("offline", null), false);
    assert.deepEqual(result, {
      formError: "We couldn't save your password. Please try again.",
      fieldErrors: {},
      linkSpent: false,
    });
  });
});
