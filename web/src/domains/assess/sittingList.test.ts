import assert from "node:assert/strict";
import { test } from "node:test";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "./vocabulary";
import {
  matchesPreset,
  modeNote,
  needsExamFirst,
  resultsWhere,
  sittingNextStep,
  type ListSitting,
  type ListResultsRow,
} from "./sittingList";

const can = { schedule: true, signOff: true };
const sitting = (over: Partial<ListSitting>): ListSitting => ({
  id: "s1",
  mode: "exam",
  status: "scheduled",
  scheduled_for: "2026-12-04T09:00:00Z",
  circuit_count: 1,
  circuits: [{ started_at: null, ended_at: null }],
  ...over,
});
const row = (over: Partial<ListResultsRow>): ListResultsRow => ({
  mode: "exam",
  candidates: 10,
  sat: 10,
  not_decided: 0,
  draft: 0,
  signed_off: 0,
  released: 0,
  ...over,
});

test("a scheduled exam with no circuits needs circuits, in hire words assessors", () => {
  const s = sitting({ circuit_count: 0, circuits: [] });
  assert.equal(sittingNextStep(s, undefined, can, INSTITUTION_WORDS), "Add circuits");
  assert.equal(sittingNextStep(s, undefined, can, EMPLOYER_WORDS), "Add assessors");
});

test("a running sitting says Running, a ready one says Run it", () => {
  const running = sitting({ status: "in_progress", circuits: [{ started_at: "t", ended_at: null }] });
  assert.equal(sittingNextStep(running, undefined, can, INSTITUTION_WORDS), "Running");
  assert.equal(sittingNextStep(sitting({}), undefined, can, INSTITUTION_WORDS), "Run it");
});

test("a finished exam walks Decide, Release, Released from the results row", () => {
  const done = sitting({ status: "completed" });
  assert.equal(sittingNextStep(done, row({ not_decided: 3 }), can, INSTITUTION_WORDS), "Decide 3");
  assert.equal(sittingNextStep(done, row({ signed_off: 10 }), can, INSTITUTION_WORDS), "Release");
  assert.equal(sittingNextStep(done, row({ released: 10 }), can, INSTITUTION_WORDS), "Released");
  assert.equal(sittingNextStep(done, undefined, can, INSTITUTION_WORDS), "Open results");
});

test("a person who cannot sign off sees the state, not the verb", () => {
  const done = sitting({ status: "completed" });
  assert.equal(sittingNextStep(done, row({ not_decided: 3 }), { schedule: false, signOff: false }, INSTITUTION_WORDS), "3 to decide");
});

test("training has no Decide or Release", () => {
  const t = sitting({ mode: "training" });
  assert.equal(sittingNextStep(t, undefined, can, INSTITUTION_WORDS), "Run it");
  assert.equal(sittingNextStep(sitting({ mode: "training", status: "completed" }), row({ mode: "training" }), can, INSTITUTION_WORDS), "Share feedback");
});

test("a cancelled sitting has no next step", () => {
  assert.equal(sittingNextStep(sitting({ status: "cancelled" }), undefined, can, INSTITUTION_WORDS), "None");
});

test("presets split upcoming, waiting for decisions and past", () => {
  const waiting = new Set(["s1"]);
  assert.equal(matchesPreset(sitting({}), "upcoming", waiting), true);
  assert.equal(matchesPreset(sitting({ status: "in_progress" }), "upcoming", waiting), true);
  assert.equal(matchesPreset(sitting({ status: "completed" }), "upcoming", waiting), false);
  assert.equal(matchesPreset(sitting({ status: "completed" }), "decisions", waiting), true);
  assert.equal(matchesPreset(sitting({ id: "s2", status: "completed" }), "decisions", waiting), false);
  assert.equal(matchesPreset(sitting({ status: "completed" }), "past", waiting), true);
  assert.equal(matchesPreset(sitting({ status: "cancelled" }), "past", waiting), true);
  assert.equal(matchesPreset(sitting({ status: "cancelled" }), "", waiting), true);
});

test("results say where each row is in words", () => {
  assert.equal(resultsWhere(row({ not_decided: 3 })), "3 decisions to make");
  assert.equal(resultsWhere(row({ not_decided: 1 })), "1 decision to make");
  assert.equal(resultsWhere(row({ draft: 2, signed_off: 8 })), "2 decisions to make");
  assert.equal(resultsWhere(row({ signed_off: 10 })), "Signed off, not released");
  assert.equal(resultsWhere(row({ signed_off: 4, released: 6 })), "Signed off, not released");
  assert.equal(resultsWhere(row({ released: 10 })), "Released");
  assert.equal(resultsWhere(row({ sat: 0, not_decided: 10 })), "Nobody has sat yet");
  assert.equal(resultsWhere(row({ mode: "training" })), "Feedback only");
});

test("the mode note shows only when both kinds exist or the viewer can schedule", () => {
  const both = [{ mode: "exam" }, { mode: "training" }];
  assert.equal(modeNote(both, false, INSTITUTION_WORDS), "Training sittings give feedback only. Decisions are made on Exam sittings.");
  assert.equal(modeNote(both, false, EMPLOYER_WORDS), "Training assessments give feedback only. Hiring decisions are made on Exam assessments.");
  assert.equal(modeNote([{ mode: "exam" }], false, INSTITUTION_WORDS), null);
  assert.notEqual(modeNote([{ mode: "exam" }], true, INSTITUTION_WORDS), null);
});

test("no active exam means the empty state asks for an exam first", () => {
  assert.equal(needsExamFirst([{ status: "draft" }]), true);
  assert.equal(needsExamFirst([]), true);
  assert.equal(needsExamFirst([{ status: "active" }]), false);
});
