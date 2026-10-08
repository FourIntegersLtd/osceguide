import assert from "node:assert/strict";
import { it } from "node:test";
import { PlatformError } from "@/foundation/platform-client";
import { actionFailureText } from "./actionFailure";

it("says what the server refused with, since retrying will not change it", () => {
  const cause = new PlatformError(404, {
    code: "station_not_found",
    message: "That station no longer exists",
    details: null,
  } as never);
  assert.equal(actionFailureText(cause), "That station no longer exists");
});

it("keeps the retry line for a dropped connection", () => {
  assert.equal(actionFailureText(new Error("network")), "Please try again in a moment.");
});
