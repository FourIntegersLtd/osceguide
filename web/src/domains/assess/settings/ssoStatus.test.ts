import assert from "node:assert/strict";
import { test } from "node:test";
import { describeSsoStatus } from "@/domains/assess/settings/ssoStatus";

test("an organisation with no arrangement is told sign-in is by password", () => {
  assert.deepEqual(describeSsoStatus({ configured: false, enabled: false, sso_only: false, sign_in_label: null }), {
    badge: "Not connected",
    tone: "neutral",
    detail: "People sign in with an email and password.",
  });
});

test("a connected arrangement says whether it is the only way in", () => {
  const status = { configured: true, enabled: true, sso_only: true, sign_in_label: "Sign in with BMJ" };
  assert.equal(describeSsoStatus(status).badge, "Connected");
  assert.equal(describeSsoStatus(status).detail, "Everyone signs in with “Sign in with BMJ”. Passwords are not accepted.");
  assert.equal(
    describeSsoStatus({ ...status, sso_only: false }).detail,
    "People can sign in with “Sign in with BMJ” or with a password.",
  );
});

test("a saved but switched-off arrangement is not called connected", () => {
  const off = { configured: true, enabled: false, sso_only: false, sign_in_label: "Sign in" };
  assert.equal(describeSsoStatus(off).badge, "Switched off");
});
