import assert from "node:assert/strict";
import { test } from "node:test";
import { readSsoCallback } from "@/capabilities/account/support/ssoCallback";

test("an Entra redirect hands on its code and the state the backend requires", () => {
  const params = new URLSearchParams("org_slug=riverside&code=0.AXo-code&state=signed.state.value&session_state=abc");
  assert.deepEqual(readSsoCallback(params), {
    ok: true,
    orgSlug: "riverside",
    token: "0.AXo-code",
    state: "signed.state.value",
  });
});

test("a Clerk redirect carries no state and still signs in", () => {
  const params = new URLSearchParams("org_slug=bmj&__clerk_session_token=tok");
  assert.deepEqual(readSsoCallback(params), { ok: true, orgSlug: "bmj", token: "tok", state: null });
});

test("a cancelled Entra sign-in says so instead of posting nothing", () => {
  const params = new URLSearchParams("org_slug=riverside&error=access_denied&state=s");
  assert.deepEqual(readSsoCallback(params), {
    ok: false,
    message: "Your organisation's sign-in did not complete. Please try again.",
  });
});

test("a SAML response the backend refused points at the set-up, not a generic retry", () => {
  const params = new URLSearchParams("org_slug=riverside&error=sso_verification_failed");
  assert.deepEqual(readSsoCallback(params), {
    ok: false,
    message:
      "Your organisation's sign-in could not be confirmed. Try again, and if it keeps happening, ask your IT team to check the single sign-on set-up.",
  });
});

test("a reload after the token was stripped says the link was used", () => {
  assert.deepEqual(readSsoCallback(new URLSearchParams("")), {
    ok: false,
    message: "This sign-in link has already been used or is incomplete. Start again from the sign-in page.",
  });
});
