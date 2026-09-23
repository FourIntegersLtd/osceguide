import { platformRequest, type components } from "@/foundation/platform-client";

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

/** A sitting binds to a programme; the exam's published rubric is resolved server-side. */
export function createSitting(
  slug: string,
  input: {
    name: string;
    mode: "training" | "exam";
    programmeId: string;
    scheduledFor: string | null;
  },
): Promise<Sitting> {
  return platformRequest<Sitting>(`${org(slug)}/sittings`, {
    method: "POST",
    body: {
      name: input.name,
      mode: input.mode,
      sitting_type: input.mode === "exam" ? "examination" : "group_training",
      programme_id: input.programmeId,
      scheduled_for: input.scheduledFor,
    },
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
 * `circuit_locked` (409) when that has happened; `readEditLock` is what lets the
 * screen say so before anybody has typed anything.
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

/** Whether a circuit's slots may be rebuilt right now, and what stops it. */
export function readEditLock(
  slug: string,
  circuitId: string,
  signal?: AbortSignal,
): Promise<components["schemas"]["EditLock"]> {
  return platformRequest<components["schemas"]["EditLock"]>(
    `${org(slug)}/circuits/${encodeURIComponent(circuitId)}/edit-lock`,
    { signal },
  );
}

/* ---------- marking ---------- */

export type SlotReview = components["schemas"]["SlotReviewRead"];
/*
 * `mine` is a PUT and nothing else: there is no read for one's own review, so
 * a screen finds it in the slot's review list by the id on it. See
 * `docs/port-gaps.md`.
 */

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
  input: { fieldValues: Record<string, unknown>; notes: string | null; status: "draft" | "submitted" },
): Promise<SlotReview> {
  return platformRequest<SlotReview>(
    `${org(slug)}/slots/${encodeURIComponent(slotId)}/reviews/mine`,
    {
      method: "PUT",
      body: { field_values: input.fieldValues, notes: input.notes, status: input.status },
    },
  );
}
