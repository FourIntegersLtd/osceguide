import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { anchoredDeadline, countdownAnchor, secondsUntil } from "@/capabilities/attempt-runner/useCountdown";

describe("anchoredDeadline", () => {
  it("starts 30 seconds short when the server says the consultation began 30 seconds ago", () => {
    const now = 1_000_000;
    const deadline = anchoredDeadline(600, { startedAtMs: now - 30_000, serverOffsetMs: 0 });
    assert.equal(secondsUntil(deadline, now), 570);
  });

  it("corrects for a device clock that runs ahead of the server's", () => {
    // Device is 5 s ahead of the server (server - device = -5 s); the server started it 30 s ago.
    const deviceNow = 2_000_000;
    const serverNow = deviceNow - 5_000;
    const deadline = anchoredDeadline(600, { startedAtMs: serverNow - 30_000, serverOffsetMs: -5_000 });
    assert.equal(secondsUntil(deadline, deviceNow), 570);
  });

  it("never goes below zero", () => {
    const deadline = anchoredDeadline(60, { startedAtMs: 0, serverOffsetMs: 0 });
    assert.equal(secondsUntil(deadline, 1_000_000), 0);
  });
});

describe("countdownAnchor", () => {
  it("is absent until the server has said when the consultation began", () => {
    assert.equal(countdownAnchor({ started_at: null, server_time: "2026-10-07T10:00:00Z" }, 0), undefined);
  });

  it("reads the offset from the brief's server_time and the moment it arrived", () => {
    const anchor = countdownAnchor(
      { started_at: "2026-10-07T10:00:00Z", server_time: "2026-10-07T10:00:30Z" },
      Date.parse("2026-10-07T10:00:35Z"),
    );
    assert.deepEqual(anchor, { startedAtMs: Date.parse("2026-10-07T10:00:00Z"), serverOffsetMs: -5_000 });
  });
});
