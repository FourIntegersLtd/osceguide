import assert from "node:assert/strict";
import { test } from "node:test";
import type { SsoSignIn } from "@/capabilities/account/api";
import {
  NO_ORG_DOOR_NOTICE,
  ORG_DOOR_UNREACHABLE_NOTICE,
  ssoForRefusedPassword,
} from "@/capabilities/account/support/ssoDiscovery";

const riverside: SsoSignIn = {
  org_slug: "riverside",
  org_name: "Riverside Trust",
  provider: "entra",
  sign_in_label: "Sign in with Riverside",
  sso_only: false,
  default_exam_code: null,
};

test("a refused password swaps the form for the organisation's button", async () => {
  const asked: string[] = [];
  const outcome = await ssoForRefusedPassword("gp@riverside.example.com", async ({ email }) => {
    asked.push(email);
    return riverside;
  });
  assert.deepEqual(asked, ["gp@riverside.example.com"]);
  assert.equal(outcome.sso?.sign_in_label, "Sign in with Riverside");
  assert.equal(outcome.sso?.sso_only, true, "the password form is hidden for this account");
  assert.equal(outcome.notice, "This organisation signs in with its own sign-in. Use the button above.");
});

test("an account with no discoverable organisation is told where to go, not refused again", async () => {
  const outcome = await ssoForRefusedPassword("gp@example.com", async () => null);
  assert.deepEqual(outcome, { sso: null, notice: NO_ORG_DOOR_NOTICE });
});

test("a failed lookup says the organisation could not be reached", async () => {
  const outcome = await ssoForRefusedPassword("gp@example.com", async () => {
    throw new Error("Gateway timeout");
  });
  assert.deepEqual(outcome, { sso: null, notice: ORG_DOOR_UNREACHABLE_NOTICE });
});
