import assert from "node:assert/strict";
import { it } from "node:test";
import { PlatformError } from "@/foundation/platform-client";
import { errorMessage } from "./useAsync";

it("gives the server's sentence for a refusal", () => {
  const cause = new PlatformError(404, {
    code: "station_not_found",
    message: "That station no longer exists",
    details: null,
  } as never);
  assert.equal(errorMessage(cause), "That station no longer exists");
});
