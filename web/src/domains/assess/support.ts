import {
  sittingTypeForMode,
  type Programme,
  type Sitting,
  type SittingChanges,
  type SittingMode,
} from "@/domains/assess/api";

/**
 * What the sitting edit form may still touch, worked out before anybody types.
 *
 * The server is the authority and will refuse anyway; this mirrors its rule so
 * the form can show a frozen field as frozen instead of inviting an edit that
 * comes back as a 409. Two different freezes, because the backend asks two
 * different questions:
 *
 * - the mode is refused while the sitting has *any* circuits at all — the mode
 *   is what a circuit's slots are composed from, and editing a sitting composes
 *   nothing (`ensure_mode_changeable`);
 * - mode, programme and sitting type are refused once a circuit has *started*
 *   (`ensure_sitting_editable`), because a mark given against the other rubric
 *   would then be read against this one.
 *
 * `started_at !== null` is exactly what `sitting_has_begun` asks — a paused or
 * finished circuit still counts. Name and date stay open for the life of the
 * record.
 */
export interface SittingEditLock {
  /** How many circuits this sitting is composed of. */
  circuits: number;
  /** Whether any of them has been started. */
  begun: boolean;
  /** The mode and the sitting type it derives from. */
  modeFrozen: boolean;
  /** Every assessment-bearing field: mode, type, programme. */
  assessmentFrozen: boolean;
}

export function sittingEditLock(sitting: Pick<Sitting, "circuits">): SittingEditLock {
  const circuits = sitting.circuits ?? [];
  const begun = circuits.some((circuit) => circuit.started_at !== null);
  return {
    circuits: circuits.length,
    begun,
    modeFrozen: begun || circuits.length > 0,
    assessmentFrozen: begun,
  };
}

/** The form's answers, in the form's words. */
export interface SittingFormValues {
  name: string;
  mode: SittingMode;
  programmeId: string;
  /** A `datetime-local` value, or "" for "not scheduled". */
  scheduledFor: string;
}

/**
 * Only what actually differs, as a partial PUT.
 *
 * The route reads a restated field as no request at all (`_requested`), so a
 * whole document would be accepted — but sending only the differences is what
 * keeps a frozen field frozen on the wire rather than relying on the server's
 * patience, and it is what makes "nothing to save" a disabled button rather
 * than a round trip.
 *
 * The date is compared as an instant, not as a string: the sitting carries
 * `2026-03-01T09:00:00Z` and the field carries `2026-03-01T09:00` in whatever
 * zone the browser is in, and those are the same appointment.
 */
export function sittingChanges(
  before: Pick<Sitting, "name" | "mode" | "programme_id" | "scheduled_for">,
  after: SittingFormValues,
): SittingChanges {
  const changes: SittingChanges = {};

  const name = after.name.trim();
  if (name.length > 0 && name !== before.name) changes.name = name;

  if (after.mode !== sittingModeOf(before.mode)) {
    changes.mode = after.mode;
    // The type is derived, not a third pick, so it moves with the mode and
    // never disagrees with it.
    changes.sittingType = sittingTypeForMode(after.mode);
  }

  if (after.programmeId && after.programmeId !== before.programme_id) {
    changes.programmeId = after.programmeId;
  }

  const scheduled = instantOf(after.scheduledFor);
  if (!sameInstant(scheduled, instantOf(before.scheduled_for))) {
    changes.scheduledFor = scheduled === null ? null : scheduled.toISOString();
  }

  return changes;
}

/** Whether a PUT of these changes would write anything. */
export function hasChanges(changes: SittingChanges): boolean {
  return Object.keys(changes).length > 0;
}

/** The sitting's mode, in the form's words. Anything else is treated as training, as the create form's default does. */
export function sittingModeOf(mode: string): SittingMode {
  return mode === "exam" ? "exam" : "training";
}

/**
 * What the programme picker may offer.
 *
 * Active programmes only — a retired one has nothing to mark with. Except the
 * one this sitting already carries: drop it and the field reads as unset, and a
 * save would move the rubric out from under marks already given against it. The
 * field is frozen anyway once the sitting has begun, so keeping it visible can
 * never silently re-point a live examination.
 */
export function programmeChoices(
  items: Programme[],
  currentId: string | null | undefined,
): Programme[] {
  return items.filter((programme) => programme.status === "active" || programme.id === currentId);
}

/** A sitting's instant as the value a `datetime-local` field shows. "" when there is no date. */
export function fieldDateTime(iso: string | null | undefined): string {
  const instant = instantOf(iso ?? null);
  if (!instant) return "";
  const pad = (part: number) => String(part).padStart(2, "0");
  return (
    `${instant.getFullYear()}-${pad(instant.getMonth() + 1)}-${pad(instant.getDate())}` +
    `T${pad(instant.getHours())}:${pad(instant.getMinutes())}`
  );
}

function instantOf(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function sameInstant(a: Date | null, b: Date | null): boolean {
  if (a === null || b === null) return a === b;
  return a.getTime() === b.getTime();
}

const SITTING_MODE_LABEL: Record<SittingMode, string> = { training: "Training", exam: "Exam" };

/** "Training" or "Exam", never the raw enum. */
export function sittingModeLabel(mode: string): string {
  return SITTING_MODE_LABEL[mode as SittingMode] ?? sentenceCase(mode);
}

/** "Scheduled", "In progress": a sitting's status as a person reads it. */
export function sittingStatusLabel(status: string): string {
  return sentenceCase(status);
}

function sentenceCase(value: string): string {
  const text = value.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}
