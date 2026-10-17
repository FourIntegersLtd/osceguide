import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { PlatformError } from "@/foundation/platform-client";
import { describeCreateSetFailure, nothingPickableMessage, trialStationsHint } from "@/domains/train/mocks/model";

describe("organisation wording", () => {
  const trial = { stations: 5, days: 21, attempts_per_station: 2 };
  const ask = "Your organisation hasn't given you access to this yet, so ask your administrator.";
  const refusal = (code: string, details?: Record<string, unknown>) =>
    new PlatformError(403, { code, message: "server wording", details } as ConstructorParameters<typeof PlatformError>[1]);

  it("never mentions a trial or subscribing to an institution's trainee", () => {
    assert.equal(nothingPickableMessage({ hasPaid: false, subscriptionExpired: false, trial, surface: "assess" }), ask);
    assert.equal(nothingPickableMessage({ hasPaid: false, subscriptionExpired: true, trial, surface: "assess" }), ask);
    assert.equal(nothingPickableMessage({ hasPaid: true, subscriptionExpired: false, trial, surface: "assess" }), "There are no stations for this exam yet.");
    assert.equal(describeCreateSetFailure(refusal("not_entitled", { reason: "trial_exhausted" }), "assess"), ask);
    assert.equal(describeCreateSetFailure(refusal("trial_station_limit", { stations_left: 1 }), "assess"), ask);
    assert.equal(trialStationsHint(2, "assess"), null);
  });
});
