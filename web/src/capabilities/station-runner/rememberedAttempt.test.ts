import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { rememberedVerdict } from "@/capabilities/station-runner/rememberedAttempt";

describe("rememberedVerdict", () => {
  it("offers a running consultation back, reuses an unstarted one", () => {
    assert.equal(rememberedVerdict("running"), "resume");
    assert.equal(rememberedVerdict("created"), "reuse");
  });

  it("never hands a finished, failed or missing attempt to the next sitting", () => {
    for (const status of ["interaction_complete", "evaluated", "failed", null]) {
      assert.equal(rememberedVerdict(status), "discard");
    }
  });
});

describe("rememberedVerdict with nothing remembered", () => {
  it("says none, not discard", () => {
    assert.equal(rememberedVerdict(undefined), "none");
  });
});
