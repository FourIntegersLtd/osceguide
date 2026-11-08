import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import type { MySitting, MySlot, TraineeResult } from "@/domains/assess/trainee/api";
import {
  BROWSER_NOTICE, finishedCopy, homeEmpty, homeHero, liveCopy, readyCopy, resultHero, resultRows, reviewNotReady, reviewTitle, stationRail, waitCopy, assessmentDesc, releasedEyebrow,
} from "@/domains/assess/trainee/hireCopy";
import { continueLabel, joinFailureCopy, modeLabel, summaryLine } from "@/domains/assess/trainee/support";
import { EMPLOYER_WORDS, INSTITUTION_WORDS } from "@/capabilities/assess-words/vocabulary";
import { PlatformError } from "@/foundation/platform-client";

const slot = (over: Partial<MySlot> & { id: string; slot_index: number }): MySlot =>
  ({ status: "scheduled", station_title: "Deteriorating patient", is_active: false, joinable: false, exam_completed_at: null, ...over }) as MySlot;
const sitting = (over: Partial<MySitting> = {}): MySitting =>
  ({ id: "s1", circuit_id: "c1", name: "Band 6 nurse assessment", mode: "exam", status: "scheduled", scheduled_for: new Date(2026, 10, 20, 9, 0).toISOString(), can_join: false, live: false, paused: false, slots: [], ...over }) as MySitting;
const five = ["Deteriorating patient", "Medicines round", "Discharge planning", "Difficult news", "Handover"].map((t, i) => slot({ id: `k${i}`, slot_index: i, station_title: t }));

test("upcoming hero reads the board's words", () => {
  const hero = homeHero([sitting({ slots: five })]);
  assert.deepEqual(hero, {
    kind: "upcoming", eyebrow: "Friday 20 November, 09:00", title: "Band 6 nurse assessment",
    meta: "5 stations. Read your brief before the day.", label: "Read your brief", path: "/trainee/sittings/s1",
  });
  assert.equal(BROWSER_NOTICE, "Use Chrome or Edge on a laptop with a microphone. You will talk to a simulated patient.");
});

test("a station open for the candidate leaves the live card to say it", () => {
  const live = sitting({ can_join: true, live: true, slots: five.map((s, i) => (i === 0 ? { ...s, is_active: true } : s)) });
  assert.equal(homeHero([live]), null);
  assert.deepEqual(liveCopy(live), {
    title: "Your assessor is ready",
    body: "Station 1 of 5 · Deteriorating patient. Join when you are ready; the clock starts when the patient speaks.",
    join: "Join station 1",
  });
});

test("a released result is the hero once nothing is left to sit", () => {
  const done = sitting({ status: "completed", released: true });
  assert.deepEqual(homeHero([done]), {
    kind: "result", eyebrow: "Released", title: "Your result is ready", meta: "Band 6 nurse assessment.", label: "See your result", path: "/trainee/results/s1",
  });
  assert.equal(homeHero([sitting({ status: "completed" })]), null);
});

test("the empty state names the employer and promises the email", () => {
  assert.deepEqual(homeEmpty("Acme Health Trust"), {
    title: "No assessments yet",
    description: "When Acme Health Trust schedules you, the date and your brief appear here and you get an email.",
  });
});

test("the assessment page: rail, wait, ready and finished", () => {
  const before = sitting({ slots: five });
  assert.deepEqual(stationRail(before).map((r) => r.label), ["1 Deteriorating patient", "2 Medicines round", "3 Discharge planning", "4 Difficult news", "5 Handover"]);
  assert.deepEqual(waitCopy(before), {
    eyebrow: "On the day", title: "Wait here for your assessor",
    body: "This page shows a Join button when your assessor starts station 1.", join: "Join station 1",
    why: "Join opens when your assessor starts the rotation.",
  });
  assert.equal(waitCopy({ ...before, paused: true }).why, "Your assessor has paused the rotation. Join opens again when they resume.");
  assert.equal(assessmentDesc(before), "Friday 20 November, 09:00 · 5 stations");
  const second = sitting({ can_join: true, slots: five.map((s, i) => ({ ...s, status: i === 0 ? "completed" : "scheduled", is_active: i === 1 })) });
  assert.deepEqual(readyCopy(second), {
    eyebrow: "Station 2 of 5 · Medicines round", title: "Ready when you are",
    body: "Read the brief, then join. The clock starts when the patient speaks.", join: "Join station 2",
  });
  assert.deepEqual(finishedCopy("Acme Health Trust"), { title: "You have finished", body: "Thank you. Acme Health Trust will tell you when your result is ready. You can close this page." });
});

const result = (extra: object = {}): TraineeResult =>
  ({
    sitting_id: "s1", released_at: "2026-10-14T10:00:00Z", acknowledged_at: null, assessment_outcome: "pass", assessment_score: 71, rationale: "Hired, offer band 6",
    stations: ["Deteriorating patient", "Medicines round", "Discharge planning", "Difficult news", "Handover"].map((t, i) => ({ slot_id: `k${i}`, station_title: t, score: 70, passed: i !== 2 })),
    ...extra,
  }) as TraineeResult;

test("the result hero is Pass · N of M stations and never the hiring decision", () => {
  const r = result({ recruitment_outcome: "hired" });
  assert.deepEqual(resultHero(r, "Acme Health Trust"), { title: "Pass · 4 of 5 stations", meta: "Acme Health Trust will contact you about next steps." });
  assert.deepEqual(resultRows(r).map((x) => [x.label, x.chip]), [
    ["1 Deteriorating patient", "Pass"], ["2 Medicines round", "Pass"], ["3 Discharge planning", "Not yet"], ["4 Difficult news", "Pass"], ["5 Handover", "Pass"],
  ]);
  const printed = JSON.stringify([resultHero(r, "Acme"), resultRows(r)]);
  assert.equal(/recruit|hired|offer/i.test(printed), false);
});

test("/me/results/{id} does not carry recruitment_outcome", () => {
  const api = JSON.parse(readFileSync(new URL("../../../../../api/openapi.json", import.meta.url), "utf8"));
  const keys = Object.keys(api.components.schemas.TraineeResultRead.properties);
  assert.equal(keys.includes("recruitment_outcome"), false);
});

test("review titles and the not-ready state", () => {
  assert.equal(reviewTitle(2, "Discharge planning"), "Station 3: Discharge planning");
  assert.deepEqual(reviewNotReady("Acme Health Trust"), {
    title: "Feedback is not ready yet",
    body: "Acme Health Trust releases feedback with your result. You will get an email when it is ready.",
    action: "Back to my assessments",
  });
});

test("hire prints no practice or mock word where a candidate reads, institution still does", () => {
  const training = sitting({ mode: "training", slots: five });
  const hire = [
    modeLabel(training, EMPLOYER_WORDS), summaryLine(training, EMPLOYER_WORDS), continueLabel(sitting({ paused: true }), EMPLOYER_WORDS),
    joinFailureCopy(new PlatformError(409, { code: "circuit_not_live", message: "x" }), EMPLOYER_WORDS),
    JSON.stringify([{ ...homeHero([sitting({ slots: five })]), path: "" }, homeEmpty("Acme"), waitCopy(sitting({ slots: five })), BROWSER_NOTICE, finishedCopy("Acme"), reviewNotReady("Acme")]),
  ].join(" ");
  assert.equal(/practi|mock|supervisor|sitting|circuit|trainee/i.test(hire), false);
  assert.equal(modeLabel(training, EMPLOYER_WORDS), "Training rotation");
  assert.equal(modeLabel(training, INSTITUTION_WORDS), "Practice circuit");
  assert.equal(continueLabel(sitting({ paused: true }), EMPLOYER_WORDS), "Paused by your assessor");
  assert.equal(continueLabel(sitting({ paused: true }), INSTITUTION_WORDS), "Paused by your supervisor");
});

test("the candidate's eyebrow says Released today only on the day", () => {
  const now = new Date("2026-11-08T15:00:00");
  assert.equal(releasedEyebrow("2026-11-08T09:00:00", now), "Released today");
  assert.equal(releasedEyebrow("2026-11-07T09:00:00", now), "Released");
  assert.equal(releasedEyebrow(null, now), "Released");
});
