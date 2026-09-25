import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { PracticeSession } from "../api";
import { latestSession, mapPhase, remainingSeconds } from "./sessionState";
import { canJoin, joinWindowClosed } from "./time";
import { phaseDurations } from "./examTimers";
const session = (overrides: Partial<PracticeSession> = {}): PracticeSession => ({
  id: "session-1", exam_code: "sca", my_role: "doctor", partner_user_id: "partner",
  room_name: "room", status: "active", partner_joined: false, feedback_state: "none", ...overrides,
});
describe("peer session recovery", () => {
  it("recognises normal completion even when the API also marks status ended", () => {
    assert.equal(mapPhase(session({ current_phase: "completed", status: "ended" })), "completed");
  });
  it("trusts server phase rather than stale partner presence", () => {
    assert.equal(mapPhase(session({ current_phase: "consultation" })), "consultation");
    assert.equal(mapPhase(session({ current_phase: "preparation" })), "preparation");
  });
  it("does not rewind after a delayed read or a stale stream frame", () => {
    const debrief = session({ current_phase: "debrief" });
    assert.equal(latestSession("session-1", debrief, session({ current_phase: "preparation" })), debrief);
    const ended = session({ status: "ended" });
    assert.equal(latestSession("session-1", ended, debrief), ended);
    assert.equal(latestSession("session-2", ended), null);
  });
  it("uses absolute server deadlines after background tab suspension", () => {
    const end = "2026-09-20T12:00:00Z";
    assert.equal(remainingSeconds(end, Date.parse(end) - 360_000), 360);
    assert.equal(remainingSeconds(end, Date.parse(end) + 10_000), 0);
    assert.equal(remainingSeconds(null, Date.now()), null);
    assert.equal(remainingSeconds("bad-date", Date.now()), null);
  });
});
describe("exam and marketplace clocks", () => {
  it("opens exactly twenty minutes before, across timezone offsets", () => {
    const start = "2026-09-20T13:00:00+01:00";
    const now = Date.parse("2026-09-20T11:40:00Z");
    assert.equal(canJoin(start, now - 1), false);
    assert.equal(canJoin(start, now), true);
    assert.equal(joinWindowClosed(start, Date.parse("2026-09-20T13:00:00Z") + 1), true);
  });
  it("matches the API timing contract for every exam", () => {
    assert.deepEqual(["sca", "plab", "casc", "ortho"].map(phaseDurations), [
      { preparation: 180, consultation: 720, debrief: 900 },
      { preparation: 120, consultation: 480, debrief: 900 },
      { preparation: 300, consultation: 420, debrief: 900 },
      { preparation: 300, consultation: 600, debrief: 900 },
    ]);
  });
});
