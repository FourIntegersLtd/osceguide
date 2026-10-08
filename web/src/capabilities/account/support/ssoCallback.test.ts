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
    loginNotice: "cancelled",
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

test("someone already signed in is told the link was not used, whatever it carries", () => {
  const callback = readSsoCallback(new URLSearchParams("org_slug=riverside&token=someone-elses"), { signedIn: true });
  assert.deepEqual(callback, {
    ok: false,
    ignored: true,
    message:
      "You're already signed in, so this organisation sign-in link was not used. To sign in as someone else, sign out first.",
  });
});

test("a cancelled Entra sign-in is handed to the sign-in page as its own notice", () => {
  const params = new URLSearchParams("org_slug=riverside&error=access_denied&state=s");
  const outcome = readSsoCallback(params);
  assert.equal(outcome.ok === false && outcome.loginNotice, "cancelled");
});
