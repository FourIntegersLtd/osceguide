import type { AssessWords } from "@/domains/assess/vocabulary";
import { humanise } from "@/foundation/format";
import { isAdminRole, isSupervisorRole } from "@/foundation/session/roles";
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
  /** The cohort the sitting is held for, or "" for none. */
  cohortId: string;
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
  before: Pick<Sitting, "name" | "mode" | "programme_id" | "scheduled_for" | "cohort_id">,
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

  if (after.cohortId !== (before.cohort_id ?? "")) changes.cohortId = after.cohortId || null;

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
  return SITTING_MODE_LABEL[mode as SittingMode] ?? humanise(mode);
}

/** "Scheduled", "In progress": a sitting's status as a person reads it. */
/** A sitting under way: the backend writes `in_progress`; `live` is the retiring label for the same. */
export function sittingRunning(status: string): boolean {
  return status === "in_progress" || status === "live";
}

/** Who a circuit's lead can be: staff, not the trainees an organisation also lists. */
export function circuitLeads<T extends { role: string }>(members: readonly T[]): T[] {
  return members.filter((member) => isAdminRole(member.role) || isSupervisorRole(member.role));
}

/** The sittings list filters the server applies (R-31); an empty field means no filter. */
export interface SittingFilters {
  status: string;
  /** "exam", "training" or "" for both. */
  mode: string;
  /** Part of the sitting's name. */
  search: string;
  programmeId: string;
  from: string;
  to: string;
}

export const NO_SITTING_FILTERS: SittingFilters = { status: "", mode: "", search: "", programmeId: "", from: "", to: "" };

export function filtersActive(filters: SittingFilters): boolean {
  return Object.values(filters).some((value) => value !== "");
}

/** The query the sittings list sends: only the filters that are set. */
export function sittingFilterQuery(filters: SittingFilters): Record<string, string> {
  const query: Record<string, string> = {};
  if (filters.status) query.status = filters.status;
  if (filters.mode) query.mode = filters.mode;
  if (filters.search.trim()) query.search = filters.search.trim();
  if (filters.programmeId) query.programme_id = filters.programmeId;
  if (filters.from) query.scheduled_from = filters.from;
  if (filters.to) query.scheduled_to = filters.to;
  return query;
}

/** Said under the sittings filters while the list is only partly loaded. */
export function sittingsScopeNote(loaded: number, hasMore: boolean): string | null {
  return hasMore && loaded > 0 ? "Covers the sittings loaded so far." : null;
}

export function sittingsEmptyDescription(canSchedule: boolean, words: AssessWords): string {
  return canSchedule
    ? "Schedule your first one."
    : `An administrator schedules ${words.sittings}; they will appear here.`;
}

export function sittingStatusLabel(status: string): string {
  return humanise(status);
}

/** A copy of `set` with `id` added, or removed if it was there. */
export function toggleInSet<T>(set: ReadonlySet<T>, id: T): Set<T> {
  const next = new Set(set);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  return next;
}

type Expandable = { id: string; user_id: string | null };

/**
 * Turn group or cohort members (roster ids) into the user ids a circuit names.
 * Members who have never signed in have no user and are counted, not added;
 * members missing from the (active-only) list are revoked and skipped.
 */
export function expandToUsers(
  memberTraineeIds: readonly string[],
  trainees: readonly Expandable[],
): { userIds: string[]; notSignedIn: number } {
  const byId = new Map(trainees.map((trainee) => [trainee.id, trainee]));
  const userIds: string[] = [];
  let notSignedIn = 0;
  for (const id of memberTraineeIds) {
    const trainee = byId.get(id);
    if (!trainee) continue;
    if (trainee.user_id === null) notSignedIn += 1;
    else userIds.push(trainee.user_id);
  }
  return { userIds, notSignedIn };
}

/** The one-line notice shown after a group or cohort is added. */
export function groupNotice(result: { userIds: readonly string[]; notSignedIn: number }): string {
  const added = `Added ${result.userIds.length}.`;
  return result.notSignedIn > 0
    ? `${added} ${result.notSignedIn} not signed in yet, so they were left out.`
    : added;
}

/** Several exam candidates become one circuit each, made in one request. */
export function isBulkExam(isExam: boolean, candidateCount: number): boolean {
  return isExam && candidateCount > 1;
}

/** A copy of `list` with the item at `index` swapped with its neighbour; unchanged if that is out of bounds. */
export function moveItem<T>(list: readonly T[], index: number, offset: -1 | 1): T[] {
  const copy = [...list];
  const target = index + offset;
  if (index < 0 || index >= copy.length || target < 0 || target >= copy.length) return copy;
  const [item] = copy.splice(index, 1);
  copy.splice(target, 0, item as T);
  return copy;
}

/** A scheduled sitting nobody is assigned to yet: its circuits are still to be built. */
export function sittingNeedsCircuits(sitting: { status: string; candidate_count: number }): boolean {
  return sitting.status === "scheduled" && sitting.candidate_count === 0;
}
