import assert from "node:assert/strict";
import { test } from "node:test";
import { afterPasswordReset } from "@/capabilities/account/support/afterPasswordReset";

test("a plain reset ends the stale local session and sends the person to sign in", async () => {
  const steps: string[] = [];
  const next = await afterPasswordReset({
    invitation: false,
    endLocalSession: async () => void steps.push("end session"),
    signIn: async () => (steps.push("sign in"), true),
  });
  assert.equal(next, "sign_in_next");
  assert.deepEqual(steps, ["end session"]);
});

test("an accepted invitation ends whoever was signed in, then signs the new account in", async () => {
  const steps: string[] = [];
  const next = await afterPasswordReset({
    invitation: true,
    endLocalSession: async () => void steps.push("end session"),
    signIn: async () => (steps.push("sign in"), true),
  });
  assert.equal(next, "signed_in");
  assert.deepEqual(steps, ["end session", "sign in"]);
});
