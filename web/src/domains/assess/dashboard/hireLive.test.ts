import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { LiveCircuit, LiveRun } from "@/domains/assess/dashboard/api";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import { earlierEmptyDescription, earlierRunText, liveCardLink, liveDescription, liveEmptyBody, liveEmptyTitle, nextSittingLine, recordingMissingAdvice, runningHeading, hireEarlierLabel, hireRowChip, hireRowStation, hireRunLine, hireWarning } from "@/domains/assess/dashboard/hireLive";

const circuit = (over: Partial<LiveCircuit>) =>
  ({
    circuit_id: "c1",
    circuit_name: "Band 6 nurse rotation",
    sitting_name: "Band 6 nurse, November intake",
    mode: "exam",
    paused: false,
    phase: "simulation",
    attempt_id: "a1",
    stations_total: 5,
    stations_completed: 2,
    current_station: { slot_id: "s", slot_index: 2, title: "Discharge planning" },
    candidates: [{ user_id: "u", name: "Tom Reid" }],
    ...over,
  }) as LiveCircuit;

describe("hire now running", () => {
  it("chips a row Live, Not joined or Paused", () => {
    assert.equal(hireRowChip(circuit({})), "Live");
    assert.equal(hireRowChip(circuit({ attempt_id: null })), "Not joined");
    assert.equal(hireRowChip(circuit({ attempt_id: null, paused: true })), "Paused");
  });
  it("names the station or says between stations", () => {
    assert.equal(hireRowStation(circuit({})), "3 of 5 · Discharge planning");
    assert.equal(hireRowStation(circuit({ current_station: null, phase: "break" })), "Between stations");
  });
  it("warns that the candidate has not joined, with how long the station has run", () => {
    const now = new Date("2026-11-08T10:03:00Z");
    assert.deepEqual(hireWarning(circuit({ attempt_id: null, phase_started_at: "2026-11-08T10:00:00Z" }), now), {
      title: "Tom Reid has not joined station 3",
      body: "The station started 3 minutes ago. Open the rotation to resend the patient or pause.",
    });
    assert.equal(hireWarning(circuit({}), now), null);
  });
  it("lines up an earlier run and labels today", () => {
    const run = (over: Partial<LiveRun>) => ({ circuit_name: "Leah Ward", stations_completed: 5, stations_total: 5, status: "ended", ...over }) as LiveRun;
    assert.equal(hireRunLine(run({})), "Leah Ward · 5 of 5 stations");
    assert.equal(hireRunLine(run({ circuit_name: "Omar Said", stations_completed: 3, status: "ended_early" })), "Omar Said · ended early at station 4");
    assert.equal(hireEarlierLabel("Today", EMPLOYER_WORDS), "Earlier today");
    assert.equal(hireEarlierLabel("Yesterday", EMPLOYER_WORDS), "Earlier · Yesterday");
  });
  it("names the candidate on an earlier run, and falls back to the circuit's name", () => {
    const run = (over: Partial<LiveRun>) => ({ circuit_name: "Rotation A", stations_completed: 5, stations_total: 5, status: "completed", ...over }) as LiveRun;
    assert.equal(hireRunLine(run({ candidates: [{ user_id: "u", name: "Leah Ward" }] })), "Leah Ward · 5 of 5 stations");
    assert.equal(
      hireRunLine(run({ stations_completed: 3, status: "ended_early", candidates: [{ user_id: "u", name: null, email: "omar@x.test" }] })),
      "omar@x.test · ended early at station 4",
    );
    assert.equal(hireRunLine(run({ candidates: [] })), "Rotation A · 5 of 5 stations");
  });
  it("says what runs next, in each arm's words", () => {
    const next = { id: "s1", name: "Band 5 nurse, December intake", scheduled_for: new Date(2026, 11, 4, 9, 0).toISOString() };
    assert.equal(nextSittingLine(next, EMPLOYER_WORDS), "The next rotation is Band 5 nurse, December intake, on 4 Dec at 09:00.");
    assert.equal(nextSittingLine(next, INSTITUTION_WORDS), null);
  });
  it("words the live board in each arm's words", () => {
    const run = { circuit_name: "Circuit A", sitting_name: "Sitting 1", mode: "exam", status: "ended", candidate_count: 1, stations_completed: 2, stations_total: 3 } as LiveRun;
    assert.equal(liveDescription(EMPLOYER_WORDS), "Every rotation running right now. This page updates by itself.");
    assert.equal(liveDescription(INSTITUTION_WORDS), "Every circuit that is live in your organisation, updated as it happens.");
    assert.equal(liveEmptyTitle(EMPLOYER_WORDS), "Nothing is running");
    assert.equal(liveEmptyTitle(INSTITUTION_WORDS), "Nothing is running.");
    assert.equal(liveEmptyBody(false, EMPLOYER_WORDS), "Rotations appear here the moment an assessor starts one.");
    assert.equal(liveEmptyBody(true, EMPLOYER_WORDS), null);
    assert.equal(liveEmptyBody(true, INSTITUTION_WORDS), "Circuits appear here the moment a supervisor starts one.");
    assert.equal(runningHeading(2, EMPLOYER_WORDS), "2 rotations running");
    assert.equal(runningHeading(1, INSTITUTION_WORDS), "1 circuit running");
    assert.equal(liveCardLink("Circuit A", EMPLOYER_WORDS), "Watch it");
    assert.equal(liveCardLink("Circuit A", INSTITUTION_WORDS), "Open Circuit A");
    assert.equal(earlierEmptyDescription(EMPLOYER_WORDS), "Rotations appear here when they end.");
    assert.equal(earlierEmptyDescription(INSTITUTION_WORDS), "Circuits appear here when they end.");
    assert.equal(hireEarlierLabel("Today", EMPLOYER_WORDS), "Earlier today");
    assert.equal(hireEarlierLabel("Today", INSTITUTION_WORDS), "Earlier · Today");
    assert.match(recordingMissingAdvice(EMPLOYER_WORDS), /^This consultation is not being recorded/);
    assert.equal(recordingMissingAdvice(INSTITUTION_WORDS), "A consultation is running but is not being recorded. Open the circuit and send the patient in again.");
    assert.deepEqual(earlierRunText(run, "Exam", EMPLOYER_WORDS), { title: "Circuit A · 2 of 3 stations", meta: "Sitting 1" });
    assert.deepEqual(earlierRunText(run, "Exam", INSTITUTION_WORDS), { title: "Circuit A", meta: "Sitting 1 · Exam · 1 candidate · 2 of 3 stations" });
  });
});
