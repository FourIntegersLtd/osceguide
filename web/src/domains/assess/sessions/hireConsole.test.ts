import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { CircuitConsole, ConsoleSlot } from "@/domains/assess/sessions/api";
import { HIRE_CONSOLE, circuitCopy, jumpChoices, hireAutoAdvance, hireEndedLine, hireMarkLabel, hireRedoDialog, HIRE_JUMP_DIALOG } from "@/domains/assess/sessions/hireConsole";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import { heroSummary } from "@/domains/assess/sessions/consoleHero";
import type { ReviewStation } from "@/domains/assess/sessions/circuitReviewSteps";

const slot = (id: string, index: number, status: string, title: string, name = "Priya Shah") =>
  ({ id, slot_index: index, status, exam_completed_at: null, trainee: { name, email: null }, station: { title } }) as unknown as ConsoleSlot;
const frame = (circuit: Record<string, unknown>, slots: ConsoleSlot[]) =>
  ({ circuit: { started_at: null, ended_at: null, paused: false, phase: null, active_slot_id: null, ...circuit }, slots }) as unknown as CircuitConsole;
const st = (position: number, state: ReviewStation["state"]): ReviewStation => ({ slotId: `s${position}`, attemptId: null, position, title: "T", state });

describe("hire console", () => {
  it("before the start the candidate waits and the primary starts the rotation", () => {
    const h = heroSummary(frame({}, [slot("a", 0, "scheduled", "NEWS2")]), [], EMPLOYER_WORDS);
    assert.deepEqual(h, { title: "Priya is in the waiting room", detail: "Start when you are ready. The patient joins as soon as you start." });
    assert.equal(HIRE_CONSOLE.start, "Start the rotation");
  });
  it("running names the station and the part", () => {
    const slots = [slot("a", 0, "completed", "NEWS2"), slot("b", 1, "in_consultation", "Medicines")];
    assert.deepEqual(heroSummary(frame({ started_at: "t", phase: "simulation", active_slot_id: "b" }, slots), [], EMPLOYER_WORDS), {
      title: "Station 2 of 2 · Medicines",
      detail: "Consultation",
    });
    assert.equal(heroSummary(frame({ started_at: "t", paused: true, phase: "simulation", active_slot_id: "b" }, slots), [], EMPLOYER_WORDS).detail, "Paused");
  });
  it("finished says how many stations to mark", () => {
    const slots = [slot("a", 0, "completed", "NEWS2")];
    assert.deepEqual(heroSummary(frame({ started_at: "t", ended_at: "u" }, slots), [st(1, "unmarked"), st(2, "unmarked"), st(3, "unmarked")], EMPLOYER_WORDS), {
      title: "Rotation finished",
      detail: "Mark 3 stations",
    });
    assert.equal(heroSummary(frame({ started_at: "t", ended_at: "u" }, slots), [st(1, "unmarked")], EMPLOYER_WORDS).detail, "Mark 1 station");
    assert.equal(heroSummary(frame({ started_at: "t", ended_at: "u" }, slots), [st(1, "marked")], EMPLOYER_WORDS).detail, "Marking finished");
  });
  it("the help line, the mark button and the auto-advance line read as the board", () => {
    assert.equal(hireEndedLine([st(1, "unmarked")]), "The AI's first marks are ready. Check each one and add your rating.");
    assert.equal(hireEndedLine([st(1, "marked")]), "Marking finished. Your marks are locked. The administrator makes the hiring decision.");
    assert.equal(hireMarkLabel(st(1, "unmarked")), "Mark station 1");
    assert.equal(hireAutoAdvance(true), "Auto-advance is on: the next station starts when the clock ends.");
    assert.equal(hireAutoAdvance(false), "Auto-advance is off: press Next station when the clock ends.");
    assert.deepEqual([HIRE_CONSOLE.menu, HIRE_CONSOLE.addTime, HIRE_CONSOLE.restartClock, HIRE_CONSOLE.end], ["If something goes wrong", "Add 2 minutes", "Restart the clock", "End rotation"]);
  });
  it("the menu offers Redo station and Jump to… as the board draws them", () => {
    assert.deepEqual(
      [HIRE_CONSOLE.redo, HIRE_CONSOLE.jump, HIRE_CONSOLE.observerLink, HIRE_CONSOLE.groups.redo, HIRE_CONSOLE.groups.jump],
      ["Redo station", "Jump to…", "Copy observer link", "The station has to be done again", "Go to another station"],
    );
    assert.deepEqual(hireRedoDialog("Medicines"), {
      title: "Redo station",
      lead: "The candidate takes Medicines again with a new patient. The first try is kept.",
    });
    assert.equal(HIRE_CONSOLE.noOtherStation, "No other station to go to");
    assert.equal(circuitCopy("Pause", EMPLOYER_WORDS), "Pause the rotation");
    assert.equal(circuitCopy("End", INSTITUTION_WORDS), "End the circuit");
    assert.equal(HIRE_JUMP_DIALOG.title, "Jump to another station");
  });
  it("Jump offers only stations not yet started, in order, never the running one", () => {
    const slots = [
      slot("c", 2, "scheduled", "Medicines"),
      slot("a", 0, "completed", "NEWS2"),
      slot("s", 1, "skipped", "Triage"),
      slot("r", 3, "in_consultation", "Handover"),
      slot("n", 4, "scheduled", "Discharge"),
    ];
    const data = frame({ active_slot_id: "r" }, slots);
    assert.deepEqual(jumpChoices(data).map((s) => s.id), ["c", "n"]);
    assert.equal(HIRE_CONSOLE.noStationRunning, "No station is running");
  });
});
