import type { MySitting, TraineeResult } from "@/domains/assess/trainee/api";
import { sittingDayLong, sittingWhenLong } from "@/domains/assess/sittingWords";
import {
  activeSlot,
  candidateDone,
  isOver,
  joinable,
  orderedSlots,
  progressOf,
  slotStatus,
  sortSittings,
} from "@/domains/assess/trainee/support";

/**
 * What a candidate reads in an employer workspace (boards HireCandidate{Home,Assessment,Result,Review}).
 *
 * Pure, so a node test pins the words. Hire-only: an institution trainee keeps the copy in `support.ts`. Nothing here
 * can carry the hiring decision: it takes only what `/me/*` returns, and `recruitment_outcome` is not in it.
 */

export const BROWSER_NOTICE =
  "Use Chrome or Edge on a laptop with a microphone. You will talk to a simulated patient.";

const stations = (n: number) => (n === 1 ? "1 station" : `${n} stations`);

type HomeHero = { kind: "upcoming" | "result"; eyebrow: string; title: string; meta: string; label: string; path: string };

/** The one hero on My assessments when no station is open: the next assessment to prepare for, else a released result. */
export function homeHero(sittings: readonly MySitting[]): HomeHero | null {
  if (sittings.some(joinable)) return null;
  const next = sortSittings(sittings).find((s) => !isOver(s) && !candidateDone(s));
  if (next) {
    const n = progressOf(next).total;
    return {
      kind: "upcoming",
      eyebrow: sittingWhenLong(next.scheduled_for, "Date to be confirmed"),
      title: next.name,
      meta: n > 0 ? `${stations(n)}. Read your brief before the day.` : "Your stations appear here once they are set.",
      label: "Read your brief",
      path: `/trainee/sittings/${next.id}`,
    };
  }
  const released = sortSittings(sittings).find((s) => s.released);
  return released
    ? { kind: "result", eyebrow: "Released", title: "Your result is ready", meta: `${released.name}.`, label: "See your result", path: `/trainee/results/${released.id}` }
    : null;
}

export const homeDesc = (org: string) => `Your assessments with ${org}, and what to do next.`;

export function homeEmpty(org: string): { title: string; description: string } {
  return { title: "No assessments yet", description: `When ${org} schedules you, the date and your brief appear here and you get an email.` };
}

/** The live card: the assessor has opened the candidate's station. */
export function liveCopy(sitting: MySitting): { title: string; body: string; join: string } {
  const slot = activeSlot(sitting);
  const total = progressOf(sitting).total;
  const place = slot ? `Station ${slot.slot_index + 1} of ${total}${slot.station_title ? ` · ${slot.station_title}` : ""}. ` : "";
  return {
    title: "Your assessor is ready",
    body: `${place}Join when you are ready; the clock starts when the patient speaks.`,
    join: slot ? `Join station ${slot.slot_index + 1}` : "Join",
  };
}

type RailItem = { id: string; label: string; now: boolean };

/** "1 Deteriorating patient", in the order they are sat; the open one is flagged. */
export function stationRail(sitting: MySitting): RailItem[] {
  return orderedSlots(sitting).map((slot) => ({
    id: slot.id,
    label: `${slot.slot_index + 1} ${slot.station_title ?? "Station"}`,
    now: slot.is_active,
  }));
}

export const BRIEF_HINT = "Each station's brief opens when the one before it ends.";

/** Before the assessor opens a station: why Join is off, and the line beneath it. */
export function waitCopy(sitting: MySitting): { eyebrow: string; title: string; body: string; join: string; why: string } {
  const slots = orderedSlots(sitting);
  const nextIndex = (slots.find((s) => !slotStatus(s).done)?.slot_index ?? 0) + 1;
  return {
    eyebrow: "On the day",
    title: "Wait here for your assessor",
    body: `This page shows a Join button when your assessor starts station ${nextIndex}.`,
    join: `Join station ${nextIndex}`,
    why: sitting.paused
      ? "Your assessor has paused the rotation. Join opens again when they resume."
      : "Join opens when your assessor starts the rotation.",
  };
}

export function readyCopy(sitting: MySitting): { eyebrow: string; title: string; body: string; join: string } {
  const slot = activeSlot(sitting);
  const total = progressOf(sitting).total;
  return {
    eyebrow: slot ? `Station ${slot.slot_index + 1} of ${total}${slot.station_title ? ` · ${slot.station_title}` : ""}` : "Today",
    title: "Ready when you are",
    body: "Read the brief, then join. The clock starts when the patient speaks.",
    join: slot ? `Join station ${slot.slot_index + 1}` : "Join",
  };
}

export const finishedCopy = (org: string) => ({
  title: "You have finished",
  body: `Thank you. ${org} will tell you when your result is ready. You can close this page.`,
});

/** "Thursday 20 November · 5 stations" under the assessment's name. */
export function assessmentDesc(sitting: MySitting): string {
  return [sitting.scheduled_for ? sittingWhenLong(sitting.scheduled_for, "") : "", stations(progressOf(sitting).total)].filter(Boolean).join(" · ");
}

/* ---------- the result ---------- */

export function outcomeLabel(outcome: string | null | undefined): string {
  if (!outcome) return "Recorded";
  return outcome.replace(/_/g, " ").replace(/^\w/, (letter) => letter.toUpperCase());
}

type ResultRow = { slotId: string; label: string; chip: string; ok: boolean };

/** "Pass · 4 of 5 stations" and the line under it. Never a hiring decision. */
export function resultHero(result: TraineeResult, org: string): { title: string; meta: string } {
  const rows = result.stations ?? [];
  const passed = rows.filter((s) => s.passed === true).length;
  const outcome = outcomeLabel(result.assessment_outcome);
  return {
    title: rows.length > 0 ? `${outcome} · ${passed} of ${rows.length} stations` : outcome,
    meta: `${org} will contact you about next steps.`,
  };
}

export function resultRows(result: TraineeResult): ResultRow[] {
  return (result.stations ?? []).map((s, i) => ({
    slotId: s.slot_id,
    label: `${i + 1} ${s.station_title ?? "Station"}`,
    chip: s.passed === true ? "Pass" : s.passed === false ? "Not yet" : s.score != null ? `${s.score.toFixed(0)} / 100` : "Not scored",
    ok: s.passed === true,
  }));
}

export const resultDesc = (releasedAt: string, org: string) => [sittingDayLong(releasedAt), `released by ${org}`].filter(Boolean).join(" · ");
export const acknowledgedCopy = (org: string) => ({ title: "Thank you", body: `${org} can see that you have read your result.` });

/* ---------- the review ---------- */

export const reviewDesc = "What your assessor saw, and what to work on.";
export const reviewTitle = (slotIndex: number | null, station: string | null | undefined) =>
  slotIndex === null ? (station ?? "Station feedback") : `Station ${slotIndex + 1}${station ? `: ${station}` : ""}`;
export const reviewNotReady = (org: string) => ({
  title: "Feedback is not ready yet",
  body: `${org} releases feedback with your result. You will get an email when it is ready.`,
  action: "Back to my assessments",
});

/** "Released today" when the results went out today, else "Released". */
export function releasedEyebrow(releasedAt: string | null | undefined, now: Date = new Date()): string {
  const at = releasedAt ? new Date(releasedAt) : null;
  return at && !Number.isNaN(at.getTime()) && at.toDateString() === now.toDateString() ? "Released today" : "Released";
}
