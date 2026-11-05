import assert from "node:assert/strict";
import { test } from "node:test";
import {
  EMPTY_DRAFT,
  circuitPlan,
  endsAbout,
  furthestStep,
  nextBreakPosition,
  peopleFormula,
  scheduledInstant,
  stepBlock,
  stepUnlocked,
  timingSummary,
  type ScheduleDraft,
} from "./scheduleSitting";

const stations = (n: number) =>
  Array.from({ length: n }, (_, i) => ({ version_id: `v${i}`, title: `Station ${i + 1}` }));
const draft = (patch: Partial<ScheduleDraft>): ScheduleDraft => ({ ...EMPTY_DRAFT, ...patch });
const words = { trainee: "trainee", trainees: "trainees" };

test("steps unlock in order, stopping at the first unanswered one", () => {
  assert.equal(furthestStep(EMPTY_DRAFT), "basics");
  assert.equal(stepUnlocked("stations", EMPTY_DRAFT), false);
  const basics = draft({ name: "Summer finals", programmeId: "p1" });
  assert.equal(furthestStep(basics), "stations");
  const withStations = { ...basics, stations: stations(2) };
  assert.equal(furthestStep(withStations), "people");
  const full = { ...withStations, candidateIds: ["u1", "u2"] };
  assert.equal(furthestStep(full), "review");
  assert.equal(stepUnlocked("review", full), true);
});

test("a training sitting needs as many trainees as stations", () => {
  const training = draft({ mode: "training", stations: stations(6), candidateIds: Array(7).fill("u") });
  assert.equal(stepBlock("people", training), "The number of trainees must match the number of stations.");
  assert.deepEqual(peopleFormula(training, words), {
    formula: "7 trainees for 6 stations.",
    help: "In training, each trainee starts at a different station, so these must match.",
    ok: false,
  });
});

test("a formal exam gives each candidate their own circuit", () => {
  const exam = draft({ mode: "exam", stations: stations(6), candidateIds: ["a", "b", "c", "d", "e", "f", "g"] });
  assert.equal(stepBlock("people", exam), null);
  assert.equal(peopleFormula(exam, words).formula, "7 candidates picked. Each gets their own circuit.");
  assert.deepEqual(circuitPlan(exam), { kind: "bulk" });
  assert.deepEqual(circuitPlan({ ...exam, perCandidate: true }).kind, "each");
  assert.deepEqual(circuitPlan({ ...exam, mode: "training" }), { kind: "training" });
});

test("timing bounds are 1 to 30, 1 to 180 and 1 to 60", () => {
  assert.equal(stepBlock("timing", draft({ readingMinutes: 31 })), "Reading time is 1 to 30 minutes.");
  assert.equal(stepBlock("timing", draft({ consultationMinutes: 181 })), "Consultation is 1 to 180 minutes.");
  assert.equal(
    stepBlock("timing", draft({ breaks: [{ after: 2, minutes: 61 }] })),
    "Each break is 1 to 60 minutes.",
  );
  assert.equal(stepBlock("timing", draft({ breaks: [{ after: 2, minutes: 5 }] })), null);
});

test("the end time adds every station and break to the start", () => {
  const timed = draft({
    stations: stations(6),
    breaks: [
      { after: 2, minutes: 5 },
      { after: 4, minutes: 15 },
    ],
  });
  assert.equal(endsAbout(timed), "10:38");
  assert.equal(timingSummary(timed), "3 + 10 min per station · breaks after 2 and 4");
  assert.equal(timingSummary(draft({})), "3 + 10 min per station");
});

test("Add a break takes the first free gap, never after the last station", () => {
  const timed = draft({ stations: stations(3), breaks: [{ after: 1, minutes: 5 }] });
  assert.equal(nextBreakPosition(timed), 2);
  assert.equal(nextBreakPosition({ ...timed, breaks: [...timed.breaks, { after: 2, minutes: 5 }] }), null);
});

test("the date and start time make one instant, or none without a date", () => {
  assert.equal(scheduledInstant({ date: "", startTime: "09:00" }), null);
  assert.equal(
    scheduledInstant({ date: "2026-11-26", startTime: "09:00" }),
    new Date("2026-11-26T09:00").toISOString(),
  );
});
