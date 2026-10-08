import assert from "node:assert/strict";
import { it } from "node:test";
import { PlatformError } from "@/foundation/platform-client";
import { joinFailureText } from "./failure";

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
