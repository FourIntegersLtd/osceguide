import { PlatformError } from "@/foundation/platform-client";
import { errorMessage } from "@/foundation/hooks/useAsync";
import type { MySitting, MySlot, OrgStation } from "@/domains/assess/trainee/api";

/**
 * The vocabulary and the arithmetic of a candidate's own view.
 *
 * Pure, because the things that decide what somebody is told before an
 * examination — whether a station counts as done, whether a room is open,
 * which sitting to put in front of them — should be testable rather than read
 * off a component. The retiring arm computed all of it inline across five
 * screens and the three copies of "is this station finished?" disagreed.
 */

export type Tone = "success" | "warning" | "danger" | "accent" | "neutral";

/* ---------- a station, as the candidate sees it ---------- */

export interface SlotStatus {
  label: string;
  tone: Tone;
  /** Finished for good. A candidate may not re-enter one. */
  done: boolean;
}

/**
 * Where one station has got to.
 *
 * `exam_completed_at` is the authority and `status` only fills in around it:
 * a slot the circuit has moved past is completed whether or not the status
 * string caught up. The old screen read the two in the opposite order and
 * offered "Join station" on stations people had already sat.
 */
export function slotStatus(slot: MySlot): SlotStatus {
  if (slot.exam_completed_at) return { label: "Completed", tone: "success", done: true };
  switch (slot.status) {
    case "completed":
      return { label: "Completed", tone: "success", done: true };
    case "in_progress":
      return { label: "In progress", tone: "accent", done: false };
    case "skipped":
      return { label: "Skipped", tone: "warning", done: true };
    case "ready":
      return { label: "Ready", tone: "accent", done: false };
    default:
      return { label: "Not started", tone: "neutral", done: false };
  }
}

/** Slots in the order they will be sat. */
export function orderedSlots(sitting: MySitting): MySlot[] {
  return [...(sitting.slots ?? [])].sort((a, b) => a.slot_index - b.slot_index);
}

export interface Progress {
  completed: number;
  total: number;
}

export function progressOf(sitting: MySitting): Progress {
  const slots = sitting.slots ?? [];
  return { completed: slots.filter((slot) => slotStatus(slot).done).length, total: slots.length };
}

/**
 * The station the candidate is on, if any.
 *
 * `is_active` is the circuit's own pointer. A sitting that is live but between
 * stations has none, which is a real state and not a missing one.
 */
export function activeSlot(sitting: MySitting): MySlot | null {
  return (sitting.slots ?? []).find((slot) => slot.is_active) ?? null;
}

/** Whether this person may enter a room right now, as the backend decided. */
export function joinable(sitting: MySitting): boolean {
  return sitting.can_join === true;
}

/* ---------- a sitting, as a row ---------- */

export const EXAM_MODES = new Set(["exam", "examination"]);

export function isExam(sitting: MySitting): boolean {
  return EXAM_MODES.has(sitting.mode);
}

export function modeLabel(sitting: MySitting): string {
  return isExam(sitting) ? "Examination" : "Practice circuit";
}

/** A sitting in one of these is over: it sorts last and belongs under "Past" (T-9). */
const FINISHED_STATUSES: readonly string[] = ["completed", "ended", "cancelled"];

export function isOver(sitting: MySitting): boolean {
  return FINISHED_STATUSES.includes(sitting.status);
}

/** Nothing left to join or prepare for: the sitting is over, or every one of this candidate's own stations is done. */
export function candidateDone(sitting: MySitting): boolean {
  const { completed, total } = progressOf(sitting);
  return isOver(sitting) || (total > 0 && completed >= total);
}

/**
 * Sittings in the order somebody wants to deal with them.
 *
 * Live first, then what is scheduled, then what is over — and within a group,
 * soonest first. A candidate with a station running should not have to scroll
 * for it.
 */
export function sortSittings(sittings: readonly MySitting[]): MySitting[] {
  return [...sittings].sort((a, b) => {
    const byPriority = priority(a) - priority(b);
    if (byPriority !== 0) return byPriority;
    return scheduledAt(a) - scheduledAt(b);
  });
}

function priority(sitting: MySitting): number {
  if (sitting.live) return 0;
  if (sitting.status === "scheduled" || sitting.status === "created") return 1;
  if (isOver(sitting)) return 3;
  return 2;
}

function scheduledAt(sitting: MySitting): number {
  const parsed = sitting.scheduled_for ? Date.parse(sitting.scheduled_for) : Number.NaN;
  return Number.isFinite(parsed) ? parsed : Number.MAX_SAFE_INTEGER;
}

/** The one thing to put in front of somebody when they arrive. */
export function spotlight(sittings: readonly MySitting[]): MySitting | null {
  return sortSittings(sittings)[0] ?? null;
}

/** Everything with a station open for this person right now. */
export function liveSittings(sittings: readonly MySitting[]): MySitting[] {
  return sittings.filter(joinable);
}

/**
 * The sitting that owns a slot, for a link that named the slot and not the sitting.
 *
 * The retiring client emailed `/b2b/trainee/join/<slotId>`, while this platform
 * opens a candidate's room by *sitting* — so a carried-over link has to be
 * resolved against the list the screen has already loaded. `MySitting.slots`
 * carries each slot's id, which makes that a lookup rather than a new endpoint.
 *
 * Answering null is a real result, not a failure: a link from last month's
 * examination points at a slot this person has since been taken off, and the
 * honest response is to say so rather than open something merely plausible.
 */
export function sittingForSlot(
  sittings: readonly MySitting[],
  slotId: string | null | undefined,
): MySitting | null {
  if (!slotId) return null;
  return sittings.find((sitting) => sitting.slots?.some((slot) => slot.id === slotId)) ?? null;
}

/** One slot within a sitting, by the id a link carried. */
export function slotById(
  sitting: MySitting,
  slotId: string | null | undefined,
): MySlot | null {
  if (!slotId) return null;
  return sitting.slots?.find((slot) => slot.id === slotId) ?? null;
}

/** Stations this person has finished, across everything they are rostered onto. */
export function stationsCompleted(sittings: readonly MySitting[]): number {
  return sittings.reduce((total, sitting) => total + progressOf(sitting).completed, 0);
}

/**
 * The subtitle under a sitting's name.
 *
 * Says what is true and nothing more: a progress count only for an
 * examination, where the candidate works through their own stations, and never
 * a count of zero for a sitting whose slots have not been published yet.
 */
export function summaryLine(sitting: MySitting): string {
  const parts = [modeLabel(sitting)];
  const { completed, total } = progressOf(sitting);
  if (isExam(sitting) && total > 0) parts.push(`${completed} of ${total} stations completed`);
  if (sitting.scheduled_for) {
    const when = new Date(sitting.scheduled_for);
    if (Number.isFinite(when.getTime())) parts.push(when.toLocaleString());
  }
  return parts.join(" · ");
}

/** What the button on the spotlight row should say. */
export function continueLabel(sitting: MySitting): string {
  if (joinable(sitting)) return "Your station is open";
  if (sitting.paused) return "Paused by your supervisor";
  if (sitting.live) return "Running now";
  const { completed, total } = progressOf(sitting);
  if (total > 0 && completed === total) return "Finished: open it for your result and feedback";
  if (completed > 0) return "Continue";
  return "Not started";
}

/**
 * What the live banner says, which differs by mode.
 *
 * In an examination the candidate walks into their own station; in a training
 * circuit only the person on turn speaks and the rest observe. Telling one
 * that they are about to be heard when they are not is how somebody sits in
 * silence waiting for a patient.
 */
export function liveBannerCopy(sitting: MySitting): { title: string; body: string } {
  if (isExam(sitting)) {
    return {
      title: "Your station is open",
      body: "Go in and read the brief. The patient joins when the reading time ends.",
    };
  }
  return {
    title: "Your turn is live",
    body: "Join the room to speak with the patient while your supervisor runs the circuit.",
  };
}

/* ---------- the clock ---------- */

/**
 * The phase, in words, when the server has named one.
 *
 * The clock itself is never computed here — `remaining_seconds` and
 * `phase_ends_at` are the server's and the browser only renders them.
 */
export function phaseLabel(phase: string | null | undefined): string {
  if (!phase) return "Now";
  const labels: Record<string, string> = {
    reading: "Reading",
    simulation: "Consultation",
    consultation: "Consultation",
    feedback: "Feedback",
    idle: "Waiting",
  };
  return labels[phase] ?? phase.replace(/_/g, " ");
}

/* ---------- self practice ---------- */

/**
 * The organisation's stations somebody may actually sit.
 *
 * A station with no published version cannot be run — `POST /attempts` refuses
 * a draft with `station_not_published` — so offering it would be a button that
 * only ever fails. Sorted by title because an org library is browsed, not
 * worked through in order.
 */
export function practisable(stations: readonly OrgStation[]): OrgStation[] {
  return stations
    .filter((station) => station.status === "published" && Boolean(station.current_version_id))
    .sort((a, b) => a.title.localeCompare(b.title));
}

/* ---------- copy ---------- */

export function greeting(now: Date): string {
  const hour = now.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

/** "Good morning, Amara." or, with no usable name, "Good morning." */
export function greetingFor(name: string | null | undefined, now: Date): string {
  const first = firstName(name);
  return first ? `${greeting(now)}, ${first}.` : `${greeting(now)}.`;
}

export function firstName(name: string | null | undefined): string | null {
  const first = (name ?? "").trim().split(/\s+/)[0];
  // Accounts invited before 2026-10-06 stored their address as the name; it is not one.
  return first && !first.includes("@") ? first : null;
}

/** Sittings still to sit or being sat, and the ones that are over (T-9). */
export function splitFinished(sittings: readonly MySitting[]): { current: MySitting[]; past: MySitting[] } {
  return { current: sittings.filter((s) => !isOver(s)), past: sittings.filter(isOver) };
}

const JOIN_REFUSALS: Record<string, string> = {
  circuit_not_live: "This circuit is not open yet. You will be let in when your supervisor starts it.",
  circuit_not_found: "That circuit is not on your list any more. Ask your organiser.",
  voice_unavailable: "The voice service is not available right now. Try again in a minute.",
  trainee_revoked: "Your access to this organisation has been withdrawn.",
  trainee_not_on_roster: "You are not on this circuit.",
};

/** Why a join was refused, in words a candidate can act on (T-7). */
export function joinFailureCopy(cause: unknown): string {
  return (cause instanceof PlatformError ? JOIN_REFUSALS[cause.code] : undefined) ?? errorMessage(cause);
}
