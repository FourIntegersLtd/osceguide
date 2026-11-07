import assert from "node:assert/strict";
import { test } from "node:test";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/domains/assess/vocabulary";
import {
  EMPTY_DRAFT,
  SCHEDULE_STEPS,
  STEP_HELP,
  scheduleWords,
  candidateStanding,
  circuitPlan,
  circuitTiming,
  eachCircuitJobs,
  freeBreakPositions,
  endsAbout,
  examTimings,
  furthestStep,
  nextBreakPosition,
  peopleFormula,
  reviewFormula,
  stationNote,
  sittingLine,
  scheduledInstant,
  startOffsetFor,
  stationAssessorsFor,
  stepBlock,
  stepUnlocked,
  timingSummary,
  type ScheduleDraft,
} from "./scheduleSitting";

const stations = (n: number) =>
  Array.from({ length: n }, (_, i) => ({ version_id: `v${i}`, title: `Station ${i + 1}` }));
const draft = (patch: Partial<ScheduleDraft>): ScheduleDraft => ({ ...EMPTY_DRAFT, ...patch });
const words = INSTITUTION_WORDS;

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
    mode: "exam",
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

test("a formal exam takes at most 200 candidates, and the step says how many to deselect", () => {
  const many = Array.from({ length: 201 }, (_, i) => `u${i}`);
  const exam = draft({ mode: "exam", stations: stations(2), candidateIds: many });
  assert.match(stepBlock("people", exam) ?? "", /at most 200 candidates.*Deselect 1\./);
  assert.equal(stepBlock("people", { ...exam, candidateIds: many.slice(0, 200) }), null);
});

test("the stored timing keeps only real gaps and non-default lengths, so review and circuit agree", () => {
  const exam = draft({
    mode: "exam",
    stations: stations(3),
    breaks: [
      { after: 1, minutes: 5 },
      { after: 3, minutes: 9 },
      { after: 2, minutes: 5 },
    ],
    breakMinutes: 5,
  });
  const timing = circuitTiming(exam);
  assert.deepEqual(timing.breaks, [1, 2]);
  assert.deepEqual(timing.breakLengths, {});
  assert.equal(timingSummary(exam), "3 + 10 min per station · breaks after 1 and 2");
  assert.deepEqual(circuitTiming({ ...exam, mode: "training" }).breaks, []);
});

test("a free gap can be chosen, and a taken one is not offered", () => {
  const timed = draft({ stations: stations(4), breaks: [{ after: 2, minutes: 5 }] });
  assert.deepEqual(freeBreakPositions(timed), [1, 3]);
});

test("a retry after a partial failure carries on from the next candidate, none twice and none skipped", () => {
  const people = ["a", "b", "c", "d"];
  assert.deepEqual(eachCircuitJobs(people, 0).map((job) => job.number), [1, 2, 3, 4]);
  // Circuits 1 and 2 were made before the failure.
  assert.deepEqual(eachCircuitJobs(people, 2), [
    { number: 3, candidate: "c" },
    { number: 4, candidate: "d" },
  ]);
  assert.deepEqual(eachCircuitJobs(people, 4), []);
});

test("a sitting starts from its exam's timings", () => {
  assert.deepEqual(
    examTimings({ default_reading_seconds: 120, default_simulation_seconds: 480, default_break_minutes: 5 }),
    { readingMinutes: 2, consultationMinutes: 8, breakMinutes: 5 },
  );
  // An exam with no break leaves the usual break.
  assert.deepEqual(
    examTimings({ default_reading_seconds: 180, default_simulation_seconds: 600, default_break_minutes: null }),
    { readingMinutes: 3, consultationMinutes: 10 },
  );
  assert.deepEqual(examTimings({ default_reading_seconds: 0, default_simulation_seconds: 0 }), {});
});

test("the station step says how many are picked and, in training, what that needs", () => {
  assert.equal(stationNote(draft({ mode: "exam", stations: stations(6) })), "6 of up to 12 stations picked.");
  assert.equal(
    stationNote(draft({ mode: "training", stations: stations(6) })),
    "6 stations picked. Training needs one trainee per station.",
  );
  assert.equal(stationNote(draft({ mode: "training", stations: stations(1) })), "1 station picked. Training needs one trainee per station.");
});

test("the review says what gets made: a circuit each for a formal exam, one shared for training", () => {
  const exam = draft({ mode: "exam", stations: stations(6), candidateIds: ["a", "b", "c", "d", "e", "f", "g"] });
  assert.deepEqual(reviewFormula(exam, "Dr Patel", words), {
    formula: "7 candidates × 6 stations → 7 circuits",
    help: "Each candidate gets their own circuit, supervised by Dr Patel.",
  });
  const training = draft({ mode: "training", stations: stations(6), candidateIds: ["a", "b", "c", "d", "e", "f"] });
  assert.deepEqual(reviewFormula(training, "Dr Patel", words), {
    formula: "6 trainees × 6 stations → 1 circuit",
    help: "Trainees rotate together round one circuit.",
  });
  assert.equal(
    reviewFormula({ ...exam, perCandidate: true }, "", words).help,
    "Each candidate gets their own circuit, with a supervisor each.",
  );
  assert.equal(reviewFormula(exam, "", words).help, "Each candidate gets their own circuit.");
});

test("sittingLine joins the name and an en-GB date, and drops a missing date", () => {
  assert.equal(sittingLine({ name: " Summer finals ", date: "2026-11-26" }), "Summer finals · 26 Nov 2026");
  assert.equal(sittingLine({ name: "Summer finals", date: "" }), "Summer finals");
});

test("candidateStanding: an invited account nobody has used is not 'signed in'", () => {
  const row = { id: "t1", email: "a@example.com", first_name: null, last_name: null };
  assert.equal(candidateStanding({ ...row, user_id: null }), "not_joined");
  assert.equal(candidateStanding({ ...row, user_id: "u1", invitation_pending: true }), "invited");
  assert.equal(candidateStanding({ ...row, user_id: "u1", invitation_pending: false }), "signed_in");
  assert.equal(candidateStanding({ ...row, user_id: "u1" }), "signed_in");
});

test("hire step copy uses hire words and never reads wrong", () => {
  const all = [...SCHEDULE_STEPS.flatMap((s) => [s.label, s.title, s.desc]), ...Object.values(STEP_HELP).flatMap((h) => [h.title, h.body])];
  for (const text of all) {
    const hire = scheduleWords(text, EMPLOYER_WORDS);
    assert.doesNotMatch(hire, /\b(sitting|supervisors?)\b/i, hire);
    assert.equal(scheduleWords(text, INSTITUTION_WORDS), text);
  }
  assert.equal(scheduleWords("Who is sitting it?", EMPLOYER_WORDS), "Who is being assessed?");
});

test("the hire review step reads rotation and assessor, never circuit or supervisor", () => {
  const exam = draft({ mode: "exam", stations: stations(6), candidateIds: ["a", "b", "c"] });
  const training = draft({ mode: "training", stations: stations(3), candidateIds: ["a", "b", "c"] });
  const lines = [
    reviewFormula(exam, "Dr Patel", EMPLOYER_WORDS),
    reviewFormula(exam, "", EMPLOYER_WORDS),
    reviewFormula({ ...exam, perCandidate: true }, "", EMPLOYER_WORDS),
    reviewFormula(training, "", EMPLOYER_WORDS),
  ].flatMap((r) => [r.formula, r.help]);
  for (const line of lines) assert.doesNotMatch(line, /\b(circuits?|supervisors?|sittings?)\b/i, line);
  assert.equal(reviewFormula(exam, "Dr Patel", EMPLOYER_WORDS).help, "Each candidate gets their own rotation, supervised by Dr Patel.");
  assert.equal(reviewFormula({ ...exam, perCandidate: true }, "", EMPLOYER_WORDS).help, "Each candidate gets their own rotation, with an assessor each.");
});

test("a stagger turns a formal exam into one circuit per candidate, each starting later", () => {
  const exam = draft({ mode: "exam", candidateIds: ["a", "b", "c"], staggerMinutes: 10, stations: stations(2) });
  assert.deepEqual(circuitPlan(exam), { kind: "each", candidateIds: ["a", "b", "c"] });
  assert.deepEqual([0, 1, 2].map((at) => startOffsetFor(exam, at)), [0, 10, 20]);
  assert.equal(circuitPlan({ ...exam, staggerMinutes: 0 }).kind, "bulk");
  assert.equal(startOffsetFor({ mode: "training", staggerMinutes: 10 }, 3), 0);
  assert.equal(startOffsetFor({ mode: "exam", staggerMinutes: 60 }, 20), 480);
});

test("only picked assessors for stations still on the draft are sent, and only for a formal exam", () => {
  const exam = draft({
    mode: "exam",
    stations: stations(2),
    stationAssessors: { v0: "", v1: "u1", gone: "u2" },
  });
  assert.deepEqual(stationAssessorsFor(exam), { v1: "u1" });
  assert.deepEqual(stationAssessorsFor({ ...exam, mode: "training" }), {});
});
