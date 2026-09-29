import {
  hasCode,
  isRouteNotServed,
  platformRequest,
  type components,
} from "@/foundation/platform-client";

export type Sitting = components["schemas"]["SittingRead"];
export type SittingPage = components["schemas"]["Page_SittingRead_"];
export type Trainee = components["schemas"]["TraineeRead"];

const org = (slug: string) => `/api/v1/orgs/${encodeURIComponent(slug)}`;

export function listSittings(slug: string, signal?: AbortSignal): Promise<SittingPage> {
  return platformRequest<SittingPage>(`${org(slug)}/sittings`, { signal });
}

export function readSitting(slug: string, sittingId: string, signal?: AbortSignal): Promise<Sitting> {
  return platformRequest<Sitting>(`${org(slug)}/sittings/${encodeURIComponent(sittingId)}`, {
    signal,
  });
}

/* ------------------------------------------------------------------------
 * Cursor paging, shared with `team/api.ts` and `roster/api.ts`.
 *
 * Every list endpoint answers `{ items, next_cursor }` and caps `limit` at a
 * hundred, so a screen that needs a whole list — the group editor, the
 * exam-access picker — walks the cursors. One helper with a ceiling, rather
 * than three copies of the loop and one of them spinning on a bad cursor.
 * --------------------------------------------------------------------- */

export interface PageParams {
  limit?: number;
  cursor?: string | null;
}

const PAGE_LIMIT = 100;
const MAX_PAGES = 25;

/** The org prefix, so the team and roster slices spell it the same way. */
export const orgPath = org;

export function pageQuery(page?: PageParams) {
  return { limit: page?.limit ?? PAGE_LIMIT, cursor: page?.cursor ?? undefined };
}

export async function collectPages<T>(
  fetchPage: (cursor: string | null) => Promise<{ items: T[]; next_cursor?: string | null }>,
): Promise<T[]> {
  const items: T[] = [];
  let cursor: string | null = null;
  for (let index = 0; index < MAX_PAGES; index += 1) {
    const page = await fetchPage(cursor);
    items.push(...page.items);
    cursor = page.next_cursor ?? null;
    if (!cursor) break;
  }
  return items;
}

export type TraineePage = components["schemas"]["Page_TraineeRead_"];
export type MembershipPage = components["schemas"]["Page_MembershipRead_"];

export function listTrainees(
  slug: string,
  signal?: AbortSignal,
  page?: PageParams,
): Promise<TraineePage> {
  return platformRequest<TraineePage>(`${org(slug)}/trainees`, { signal, query: pageQuery(page) });
}

export function listMemberships(
  slug: string,
  signal?: AbortSignal,
  page?: PageParams,
): Promise<MembershipPage> {
  return platformRequest<MembershipPage>(`${org(slug)}/memberships`, {
    signal,
    query: pageQuery(page),
  });
}

export type Programme = components["schemas"]["ProgrammeRead"];

export function listProgrammes(slug: string, signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_ProgrammeRead_"]>(
    `${org(slug)}/programmes`,
    { signal },
  );
}

/**
 * The sitting type that goes with a mode.
 *
 * The retiring client had a session type and a mode as two independent picks;
 * here the one is derived from the other, which is what `NewSitting` already
 * did inline and what the edit form must keep doing — two screens disagreeing
 * about the derivation is how a sitting ends up `exam` typed `group_training`.
 */
export function sittingTypeForMode(mode: SittingMode): string {
  return mode === "exam" ? "examination" : "group_training";
}

/** A sitting's mode, in the words the form and the API share. */
export type SittingMode = "training" | "exam";

/**
 * A sitting binds to a programme; the exam's published rubric is resolved server-side.
 */
export function createSitting(
  slug: string,
  input: {
    name: string;
    mode: SittingMode;
    programmeId: string;
    scheduledFor: string | null;
  },
): Promise<Sitting> {
  return platformRequest<Sitting>(`${org(slug)}/sittings`, {
    method: "POST",
    body: {
      name: input.name,
      mode: input.mode,
      sitting_type: sittingTypeForMode(input.mode),
      programme_id: input.programmeId,
      scheduled_for: input.scheduledFor,
    },
  });
}

/**
 * What the edit screen may ask to change.
 *
 * A partial PUT: a field that is absent is left alone, which is what the
 * retiring route meant too. `scheduledFor: null` is a real request to clear
 * the date — "not scheduled" is a state a sitting can be in — while a null on
 * any of the others is the schema's default read as "not asked for", which is
 * why they are `undefined` here and not nullable. `status` is deliberately
 * absent: that belongs to the run machine, and a route that could set it would
 * let a screen end an examination by editing a name.
 *
 * The refusals, all of them surfaced by the form rather than retried:
 * `sitting_locked` (409) — an assessment-bearing field was sent after a circuit
 * started; `invalid_circuit` (409) — the mode was sent while circuits exist,
 * which would relabel what they are; `exam_rubric_not_ready` and
 * `rubric_version_not_published` — the new programme has nothing to mark with.
 */
export interface SittingChanges {
  name?: string;
  mode?: SittingMode;
  sittingType?: string;
  scheduledFor?: string | null;
  programmeId?: string;
}

export function updateSitting(
  slug: string,
  sittingId: string,
  changes: SittingChanges,
): Promise<Sitting> {
  const body: components["schemas"]["UpdateSitting"] = {};
  if (changes.name !== undefined) body.name = changes.name;
  if (changes.mode !== undefined) body.mode = changes.mode;
  if (changes.sittingType !== undefined) body.sitting_type = changes.sittingType;
  // `null` is meaningful on this one field, so it is tested for absence and not
  // for truthiness.
  if (changes.scheduledFor !== undefined) body.scheduled_for = changes.scheduledFor;
  if (changes.programmeId !== undefined) body.programme_id = changes.programmeId;

  return platformRequest<Sitting>(`${org(slug)}/sittings/${encodeURIComponent(sittingId)}`, {
    method: "PUT",
    body,
  });
}

export type Circuit = components["schemas"]["CircuitRead"];

/**
 * A circuit's shape, in the words the builder uses.
 *
 * One type for both writes, because creating one and changing one are the same
 * question — who is on it, which stations, for how long — and the second is only
 * allowed to answer it while nothing on the circuit means anything yet.
 */
export interface CircuitShape {
  name: string;
  stationVersionIds: string[];
  /** `user` ids, not roster ids: a slot names a user. */
  traineeIds: string[];
  supervisorUserId: string | null;
  timing: CircuitTiming;
}

/**
 * The clock, in the builder's words.
 *
 * `breaks` are 1-based station numbers the break falls *after*, and
 * `breakMinutes` is one length for all of them — the platform's `Timing` carries
 * a single `break_minutes` where the retiring client carried a duration per
 * break. `sittings/domain.py` drops both outside exam mode and clamps them
 * inside it; `domains/assess/timing.ts` mirrors that so the form only offers
 * answers the server will keep.
 */
export interface CircuitTiming {
  readingMinutes: number;
  simulationMinutes: number;
  breakMinutes: number;
  breaks: number[];
}

/**
 * Add a circuit to a sitting.
 *
 * An exam circuit is one candidate through every station, capped at twelve. A
 * training circuit pairs each trainee with one station positionally and they
 * rotate — which is why the two lists are sent as they are and the backend
 * builds the slots.
 */
export function createCircuit(
  slug: string,
  sittingId: string,
  input: CircuitShape,
): Promise<Circuit> {
  return platformRequest<Circuit>(
    `${org(slug)}/sittings/${encodeURIComponent(sittingId)}/circuits`,
    {
      method: "POST",
      body: {
        name: input.name,
        station_version_ids: input.stationVersionIds,
        trainee_ids: input.traineeIds,
        supervisor_user_id: input.supervisorUserId,
        timing: {
          reading_minutes: input.timing.readingMinutes,
          simulation_minutes: input.timing.simulationMinutes,
          break_minutes: input.timing.breakMinutes,
          breaks: input.timing.breaks,
        },
      },
    },
  );
}

/**
 * Change a circuit that already exists.
 *
 * The slots are rebuilt from scratch, so `trainee_ids` and
 * `station_version_ids` go whole rather than as a patch — the same rule create
 * follows, and the reason this is refused once a consultation has run, a station
 * has been sat, or feedback has been recorded. The backend answers
 * `circuit_locked` (409) when that has happened; the edit screen knows sooner
 * because it reads `editable`/`edit_block` off the console frame it already
 * loads, so it can say so before anybody has typed anything.
 *
 * This route existed on platform-api and nothing in the product called it, which
 * is how "a circuit cannot be corrected" looked like a backend limitation rather
 * than a missing screen.
 */
export function rebuildCircuit(
  slug: string,
  circuitId: string,
  input: CircuitShape,
): Promise<Circuit> {
  return platformRequest<Circuit>(`${org(slug)}/circuits/${encodeURIComponent(circuitId)}`, {
    method: "PUT",
    body: {
      name: input.name,
      station_version_ids: input.stationVersionIds,
      trainee_ids: input.traineeIds,
      supervisor_user_id: input.supervisorUserId,
      timing: {
        reading_minutes: input.timing.readingMinutes,
        simulation_minutes: input.timing.simulationMinutes,
        break_minutes: input.timing.breakMinutes,
        breaks: input.timing.breaks,
      },
    },
  });
}

/* ---------- marking ---------- */

export type SlotReview = components["schemas"]["SlotReviewRead"];
export type Transcript = components["schemas"]["TranscriptRead"];

/**
 * The examiner's read of what was actually said.
 *
 * `capabilities/attempt-runner` already calls this route for the candidate who
 * sat it, and the route used to answer anybody else with `attempt_not_yours` —
 * which is why the marking was reviewable and the consultation underneath it
 * was not. The authorisation is now widened to exactly one other person: the
 * supervisor named on the attempt's circuit. This is that reader's call, kept
 * in the assess slice because the assess screens are the ones that need it and
 * the runner module above them is a candidate's module.
 *
 * Nothing here decides who may read it; the server does, and a refusal is
 * surfaced by the screen rather than retried.
 */
export function readAttemptTranscript(
  attemptId: string,
  signal?: AbortSignal,
): Promise<Transcript> {
  return platformRequest<Transcript>(
    `/api/v1/attempts/${encodeURIComponent(attemptId)}/transcript`,
    { signal },
  );
}
/**
 * This examiner's own review of a slot, or `null` for none yet.
 *
 * `GET …/reviews/mine` is the read beside the PUT (backend branch
 * `feat/backend-backlog-batch-1`). `undefined` means that route is not
 * deployed yet, and the caller finds the review in the slot's list by the id
 * on it, as screens did before.
 */
export async function readMySlotReview(
  slug: string,
  slotId: string,
  signal?: AbortSignal,
): Promise<SlotReview | null | undefined> {
  try {
    return await platformRequest<SlotReview>(
      `${org(slug)}/slots/${encodeURIComponent(slotId)}/reviews/mine`,
      { signal },
    );
  } catch (error) {
    if (hasCode(error, "review_not_found")) return null;
    if (isRouteNotServed(error)) return undefined;
    throw error;
  }
}

/**
 * Save or submit a review.
 *
 * `draft` is savable as often as you like; `submitted` is the assertion. The
 * backend refuses a submit that has not scored what the sitting's template
 * requires, so the frontend does not re-derive that rule.
 */
export function saveReview(
  slug: string,
  slotId: string,
  input: { fieldValues: Record<string, unknown>; notes: string | null; status: "draft" | "completed" },
): Promise<SlotReview> {
  return platformRequest<SlotReview>(
    `${org(slug)}/slots/${encodeURIComponent(slotId)}/reviews/mine`,
    {
      method: "PUT",
      body: { field_values: input.fieldValues, notes: input.notes, status: input.status },
    },
  );
}
