import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { phaseDeadline, secondsLeft } from "@/foundation/ui/phaseCountdown";

const NOW = Date.parse("2026-10-18T10:00:00Z");

describe("phase countdown", () => {
  it("starts from the time the server says is left, not the full phase", () => {
    // 10-minute consultation, 90 s already used by the server's clock.
    assert.equal(secondsLeft(phaseDeadline(600, 90, NOW), NOW), 510);
  });

  it("measures from the wall clock, so a throttled tab that missed every tick is still right", () => {
    const deadline = phaseDeadline(600, 90, NOW);
    assert.equal(secondsLeft(deadline, NOW + 45_000), 465);
    assert.equal(secondsLeft(deadline, NOW + 45_400), 465);
  });

  it("ages the server's answer from when it arrived, so a later remount does not hand time back", () => {
    // Brief read at NOW (90 s used); the timer mounts again two minutes later.
    assert.equal(secondsLeft(phaseDeadline(600, 90, NOW), NOW + 120_000), 390);
  });

  it("never goes below zero, even when the server says the phase is long over", () => {
    assert.equal(secondsLeft(phaseDeadline(600, 900, NOW), NOW), 0);
    assert.equal(secondsLeft(phaseDeadline(600, 90, NOW), NOW + 600_000), 0);
  });
});
