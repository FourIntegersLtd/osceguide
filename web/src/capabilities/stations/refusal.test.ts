import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { PlatformError } from "@/foundation/platform-client";
import { describeRefusal } from "@/capabilities/stations/refusal";

const START_FALLBACK = "We could not start this station. Please try again.";
const describeStartFailure = (cause: unknown) => describeRefusal(cause, START_FALLBACK);

type Body = ConstructorParameters<typeof PlatformError>[1];
const refusal = (status: number, code: string, details?: Record<string, unknown>) =>
  new PlatformError(status, { code, message: "server wording", details } as Body);

describe("describeRefusal", () => {
  it("explains a used-up trial, an ended grant and no access separately", () => {
    assert.match(describeStartFailure(refusal(403, "not_entitled", { reason: "trial_exhausted" })), /used up/);
    assert.match(describeStartFailure(refusal(403, "not_entitled", { reason: "expired" })), /has ended/);
    assert.match(describeStartFailure(refusal(403, "not_entitled", { reason: "no_entitlement" })), /do not have access/);
  });

  it("explains a locked session", () => {
    assert.match(describeRefusal(refusal(409, "set_locked"), "x"), /locked because your access has ended/);
  });

  it("never shows a consumer the circuit builder's wording for an unpublished station", () => {
    const text = describeStartFailure(refusal(409, "station_not_published"));
    assert.doesNotMatch(text, /circuit/i);
    assert.match(text, /not available/);
  });

  it("tells a learner a station from another exam is no longer part of this one", () => {
    assert.match(describeStartFailure(refusal(409, "station_exam_mismatch")), /no longer part of this exam/);
  });

  it("falls back to the server's message, then to a generic one", () => {
    assert.equal(describeStartFailure(refusal(500, "internal_error")), "server wording");
    assert.equal(describeStartFailure(undefined), "We could not start this station. Please try again.");
  });
});
