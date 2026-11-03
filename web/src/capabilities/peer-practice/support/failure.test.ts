import assert from "node:assert/strict";
import { it } from "node:test";
import { PlatformError } from "@/foundation/platform-client";
import { failureText, joinFailureText } from "./failure";

function refusal(code: string, status: number, message: string): PlatformError {
  return new PlatformError(status, { code, message, details: null } as never);
}

it("tells somebody joining an exam with no stations that retrying will not help", () => {
  const cause = refusal("no_stations_for_exam", 409, "There are no stations to practise for that exam yet");
  assert.equal(joinFailureText(cause), "There are no stations to practise for that exam yet");
});

it("keeps the generic retry line for a failure with nothing useful to say", () => {
  assert.equal(joinFailureText(new Error("network")), "Please try again in a moment.");
});

it("tells somebody whose free trial has ended that peer practice is closed and what to do", () => {
  const cause = new PlatformError(403, { code: "not_entitled", message: "You do not have access to this exam", details: { reason: "trial_expired" } } as never);
  assert.match(failureText(cause, "Failed to claim slot."), /free trial has ended/);
  assert.match(joinFailureText(cause), /free trial has ended/);
});

it("tells somebody with no access to ask for it or subscribe, not just that they lack it", () => {
  const cause = new PlatformError(403, { code: "not_entitled", message: "You do not have access to this exam", details: { reason: "no_entitlement" } } as never);
  assert.match(failureText(cause, "x"), /Ask your organisation for access, or subscribe/);
});
