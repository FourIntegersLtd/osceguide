import assert from "node:assert/strict";
import { test } from "node:test";
import { signInRedirect } from "@/foundation/routing/sessionGate";

test("a signed-out visit to the app goes to sign-in and comes back after", () => {
  assert.equal(signInRedirect("/app/personal/stations", "?tab=a", false), "/login?next=%2Fapp%2Fpersonal%2Fstations%3Ftab%3Da");
  assert.equal(signInRedirect("/app", "", false), "/login?next=%2Fapp");
});

test("a visit with a session cookie is left to the app and the API", () => {
  assert.equal(signInRedirect("/app/personal", "", true), null);
});

test("the public site and look-alike paths are never gated", () => {
  assert.equal(signInRedirect("/", "", false), null);
  assert.equal(signInRedirect("/pricing", "", false), null);
  assert.equal(signInRedirect("/application-notes", "", false), null);
  assert.equal(signInRedirect("/login", "", false), null);
});
