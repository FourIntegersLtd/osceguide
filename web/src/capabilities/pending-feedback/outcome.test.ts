import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { MAX_WAIT_MS, pendingOutcome } from "@/capabilities/pending-feedback/outcome";

describe("pendingOutcome", () => {
  it("reports a failed attempt as failed, not expired", () => {
    assert.equal(pendingOutcome({ resultCount: 0, attemptStatus: "failed", elapsedMs: 1000 }), "failed");
  });

  it("expires only a job that never settled in time", () => {
    assert.equal(pendingOutcome({ resultCount: 0, attemptStatus: "marking", elapsedMs: MAX_WAIT_MS }), "expired");
    assert.equal(pendingOutcome({ resultCount: 0, attemptStatus: "marking", elapsedMs: 1000 }), "waiting");
  });

  it("a result wins over everything", () => {
    assert.equal(pendingOutcome({ resultCount: 1, attemptStatus: "failed", elapsedMs: MAX_WAIT_MS }), "ready");
  });
});
