import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { PlatformError } from "@/foundation/platform-client";
import { describeStartFailure } from "@/capabilities/station-runner/startFailure";

type Body = ConstructorParameters<typeof PlatformError>[1];
const refusal = (status: number, code: string, details?: Record<string, unknown>) =>
  new PlatformError(status, { code, message: "server wording", details } as Body);

describe("describeStartFailure", () => {
  it("explains a used-up trial, an ended grant and no access separately", () => {
    assert.match(describeStartFailure(refusal(403, "not_entitled", { reason: "trial_exhausted" })), /used up/);
    assert.match(describeStartFailure(refusal(403, "not_entitled", { reason: "expired" })), /has ended/);
    assert.match(describeStartFailure(refusal(403, "not_entitled", { reason: "no_entitlement" })), /do not have access/);
  });

  it("never shows a consumer the circuit builder's wording for an unpublished station", () => {
    const text = describeStartFailure(refusal(409, "station_not_published"));
    assert.doesNotMatch(text, /circuit/i);
    assert.match(text, /not available/);
  });

  it("falls back to the server's message, then to a generic one", () => {
    assert.equal(describeStartFailure(refusal(500, "internal_error")), "server wording");
    assert.equal(describeStartFailure(undefined), "We could not start this station. Please try again.");
  });
});
