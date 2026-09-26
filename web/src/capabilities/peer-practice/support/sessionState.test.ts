import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { PracticeSession } from "../api";
import { endingAbandons, latestSession, mapPhase, phaseLabel, phaseTitle, remainingSeconds, sessionExit } from "./sessionState";
import { canJoin, joinWindowClosed } from "./time";
import { phaseDurations } from "./examTimers";
const session = (overrides: Partial<PracticeSession> = {}): PracticeSession => ({
  id: "session-1", exam_code: "sca", my_role: "doctor", partner_user_id: "partner",
  room_name: "room", status: "active", partner_joined: false, feedback_state: "none", my_accepted: true, partner_accepted: true, ...overrides,
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
    const matched = session({ status: "matched" });
    assert.equal(latestSession("session-1", matched, session({ status: "pending_accept" })), matched);
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

describe("how a session ends", () => {
  it("abandons before the consultation and with more than three minutes of it left", () => {
    assert.equal(endingAbandons("waiting_partner", null), true);
    assert.equal(endingAbandons("preparation", 90), true);
    assert.equal(endingAbandons("consultation", 181), true);
    assert.equal(endingAbandons("consultation", 180), false);
    assert.equal(endingAbandons("debrief", 600), false);
  });
  it("sends the leaver to the dashboard and offers the partner a requeue", () => {
    const abandoned = session({ status: "ended", end_reason: "abandoned" });
    assert.deepEqual(sessionExit(abandoned, true), { kind: "dashboard" });
    assert.deepEqual(sessionExit(abandoned, false), { kind: "partner_gone", reason: "partner_left" });
    assert.deepEqual(sessionExit(session({ status: "ended", end_reason: "declined" }), false), { kind: "partner_gone", reason: "no_response" });
    assert.deepEqual(sessionExit(session({ status: "cancelled" }), false), { kind: "partner_gone", reason: "no_response" });
    assert.deepEqual(sessionExit(session({ status: "ended", end_reason: "no_response", requeued_entry_id: "entry-9" }), false), { kind: "requeued", entryId: "entry-9" });
    assert.deepEqual(sessionExit(session({ status: "ended", end_reason: "declined", requeued_entry_id: "entry-9" }), false), { kind: "requeued", entryId: "entry-9" });
  });
  it("sends every other ending to feedback, and a live session nowhere", () => {
    assert.deepEqual(sessionExit(session({ current_phase: "completed", status: "ended" }), false), { kind: "feedback" });
    assert.deepEqual(sessionExit(session({ status: "ended", end_reason: "ended_by_participant" }), false), { kind: "feedback" });
    assert.deepEqual(sessionExit(session({ current_phase: "consultation" }), false), { kind: "stay" });
  });
});

describe("session header", () => {
  it("names a match that fell through, behind the \"no longer available\" modal", () => {
    const declined = session({ status: "ended", end_reason: "declined", ended_at: "2026-09-26T10:00:00Z", requeued_entry_id: "entry-2" });
    assert.equal(sessionExit(declined, false).kind, "requeued");
    assert.equal(phaseLabel(mapPhase(declined)), "Ended");
    assert.equal(phaseTitle(mapPhase(declined)), "Session Ended");
  });
  it("captions every live phase", () => {
    assert.equal(phaseLabel("waiting_partner"), "Reading");
    assert.equal(phaseLabel("preparation"), "Reading");
    assert.equal(phaseLabel("consultation"), "Simulation");
    assert.equal(phaseLabel("debrief"), "Debrief");
    assert.equal(phaseLabel("completed"), "Ended");
  });
});
