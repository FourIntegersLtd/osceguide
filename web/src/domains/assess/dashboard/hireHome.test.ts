import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { EMPLOYER_WORDS } from "@/capabilities/assess-words/vocabulary";
import { hireRail, hireRailNext } from "@/domains/assess/dashboard/setupSteps";
import { laterToday } from "@/domains/assess/dashboard/support";
import type { OrgSetup, SupervisorCircuitRow } from "@/domains/assess/dashboard/api";

const setup = (over: Partial<OrgSetup>): OrgSetup =>
  ({ programme_exam_rubric_ready: false, stations_available: false, trainees_added: false, team_invited: false, sitting_scheduled: false, ready_to_run: false, ...over }) as OrgSetup;

describe("hire home rail", () => {
  it("is Exam, Candidates, Assessors, Assessment and asks for the exam first", () => {
    const steps = hireRail(setup({}), EMPLOYER_WORDS);
    assert.deepEqual(steps.map((s) => s.label), ["Exam", "Candidates", "Assessors", "Assessment"]);
    assert.equal(hireRailNext(steps)?.cta, "Set up an exam");
    assert.equal(steps[3]?.blocked, "You need an exam, stations and candidates first.");
  });
  it("moves to Add candidates, then Schedule an assessment, and skips the optional assessors", () => {
    const exam = { programme_exam_rubric_ready: true, stations_available: true, ready_to_run: true };
    assert.equal(hireRailNext(hireRail(setup(exam), EMPLOYER_WORDS))?.cta, "Add candidates");
    const next = hireRailNext(hireRail(setup({ ...exam, trainees_added: true }), EMPLOYER_WORDS));
    assert.equal(next?.cta, "Schedule an assessment");
    assert.equal(next?.blocked, null);
    assert.equal(hireRailNext(hireRail(setup({ ...exam, trainees_added: true, sitting_scheduled: true }), EMPLOYER_WORDS)), null);
  });
});

describe("assessor home", () => {
  it("lists the rotations after the first that are still to run today", () => {
    const at = (h: number) => new Date(2026, 10, 20, h).toISOString();
    const row = (id: string, h: number, ended = false) => ({ circuit_id: id, scheduled_for: at(h), ended, in_progress: false }) as SupervisorCircuitRow;
    const later = laterToday([row("a", 10), row("b", 11), row("c", 13), row("d", 9, true)], new Date(2026, 10, 20, 8));
    assert.deepEqual(later.map((r) => r.circuit_id), ["b", "c"]);
  });
});

describe("hire rail Assessment step", () => {
  it("names what is missing, not just the exam", () => {
    const blocked = (over: Partial<OrgSetup>) => hireRail(setup(over), EMPLOYER_WORDS).find((s) => s.id === "assessment")?.blocked;
    assert.equal(blocked({}), "You need an exam, stations and candidates first.");
    assert.equal(blocked({ programme_exam_rubric_ready: true, stations_available: true }), "You need candidates first.");
    assert.equal(blocked({ programme_exam_rubric_ready: true, stations_available: true, trainees_added: true }), "You need your team first.");
    assert.equal(blocked({ programme_exam_rubric_ready: true, stations_available: true, trainees_added: true, ready_to_run: true }), null);
  });
});
