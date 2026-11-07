import {
  collectPages,
  platformRequest,
  type components,
} from "@/foundation/platform-client";
import type { StationLibraryScope } from "@/capabilities/stations";

export type Sitting = components["schemas"]["SittingRead"];
export type SittingPage = components["schemas"]["Page_SittingRead_"];
export type Trainee = components["schemas"]["TraineeRead"];

const org = (slug: string) => `/api/v1/orgs/${encodeURIComponent(slug)}`;

export type Organization = components["schemas"]["OrganizationRead"];

export type SsoStatus = components["schemas"]["SsoStatusRead"];

export function readSsoStatus(
  slug: string,
  signal?: AbortSignal,
): Promise<SsoStatus> {
  return platformRequest<SsoStatus>(`${org(slug)}/sso-status`, { signal });
}

/** An organisation's own admin renames it; the web address and contract are staff's (B-33). */
export function renameOrganization(
  slug: string,
  name: string,
): Promise<Organization> {
  return platformRequest<Organization>(org(slug), {
    method: "PATCH",
    body: { name },
  });
}

/** The organisation itself: its name, type and sign-in rules. */
export function readOrganization(
  slug: string,
  signal?: AbortSignal,
): Promise<Organization> {
  return platformRequest<Organization>(org(slug), { signal });
}

export function listSittings(
  slug: string,
  signal?: AbortSignal,
  page?: PageParams,
  filters: Record<string, string> = {},
): Promise<SittingPage> {
  const { limit, cursor } = pageQuery(page);
  return platformRequest<SittingPage>(`${org(slug)}/sittings`, {
    signal,
    query: { limit, cursor, ...filters },
  });
}

export function readSitting(
  slug: string,
  sittingId: string,
  signal?: AbortSignal,
): Promise<Sitting> {
  return platformRequest<Sitting>(
    `${org(slug)}/sittings/${encodeURIComponent(sittingId)}`,
    {
      signal,
    },
  );
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
  /** Matched in SQL, so a screen never has to load a page to filter it away. */
  search?: string | null;
}

const PAGE_LIMIT = 100;

/** The org prefix, so the team and roster slices spell it the same way. */
export const orgPath = org;

export function pageQuery(page?: PageParams) {
  return {
    limit: page?.limit ?? PAGE_LIMIT,
    cursor: page?.cursor ?? undefined,
    search: page?.search?.trim() || undefined,
  };
}

export type TraineePage = components["schemas"]["TraineePage"];
export type MembershipPage = components["schemas"]["Page_MembershipRead_"];

/** `accessRevoked: false` narrows to trainees who still have access, in SQL. */
export function listTrainees(
  slug: string,
  signal?: AbortSignal,
  page?: PageParams & { accessRevoked?: boolean | null },
): Promise<TraineePage> {
  return platformRequest<TraineePage>(`${org(slug)}/trainees`, {
    signal,
    query: {
      ...pageQuery(page),
      access_revoked: page?.accessRevoked ?? undefined,
    },
  });
}

/** `status: "active"` narrows to staff who have not been revoked, in SQL. */
export function listMemberships(
  slug: string,
  signal?: AbortSignal,
  page?: PageParams & { status?: string | null },
): Promise<MembershipPage> {
  return platformRequest<MembershipPage>(`${org(slug)}/memberships`, {
    signal,
    query: { ...pageQuery(page), status: page?.status ?? undefined },
  });
}

/**
 * Everyone on the roster who still has access, every page of it. The circuit
 * pickers read the first page only and dropped everyone past the hundredth.
 */
export function listActiveTrainees(
  slug: string,
  signal?: AbortSignal,
): Promise<Trainee[]> {
  return collectPages((cursor) =>
    listTrainees(slug, signal, { cursor, accessRevoked: false }),
  );
}

/** The active team, every page of it, for the supervisor picker. */
export function listActiveMembers(
  slug: string,
  signal?: AbortSignal,
): Promise<MembershipPage["items"]> {
  return collectPages((cursor) =>
    listMemberships(slug, signal, { cursor, status: "active" }),
  );
}

export type Programme = components["schemas"]["ProgrammeRead"];

/** Every programme, every page: a first page of 25 hid the rest from the sitting pickers (S-27). */
export async function listProgrammes(slug: string, signal?: AbortSignal) {
  const items = await collectPages((cursor) =>
    platformRequest<components["schemas"]["Page_ProgrammeRead_"]>(
      `${org(slug)}/programmes`,
      {
        signal,
        query: { limit: PAGE_LIMIT, cursor: cursor ?? undefined },
      },
    ),
  );
  return { items };
}

/**
 * Where a sitting's station library reads from. An exam the organisation wrote
 * itself has no platform stations, so that leg is skipped rather than asked and
 * refused; a programme that cannot be found keeps it (the server still decides).
 */
export async function sittingLibraryScope(
  slug: string,
  sitting: { programme_id?: string | null; exam_code?: string | null },
  signal?: AbortSignal,
): Promise<StationLibraryScope> {
  const programmes = await listProgrammes(slug, signal);
  const programme = programmes.items.find(
    (item) => item.id === sitting.programme_id,
  );
  return {
    orgSlug: slug,
    examCode: sitting.exam_code ?? null,
    orgOwnedExam: programme?.exam_owner_kind === "org",
  };
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
    cohortId?: string | null;
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
      ...(input.cohortId ? { cohort_id: input.cohortId } : {}),
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
  /** `null` takes the sitting off its cohort. */
  cohortId?: string | null;
}

export function updateSitting(
  slug: string,
  sittingId: string,
  changes: SittingChanges,
  revision?: number,
): Promise<Sitting> {
  const body: components["schemas"]["UpdateSitting"] & {
    cohort_id?: string | null;
  } = { revision };
  if (changes.name !== undefined) body.name = changes.name;
  if (changes.mode !== undefined) body.mode = changes.mode;
  if (changes.sittingType !== undefined)
    body.sitting_type = changes.sittingType;
  // `null` is meaningful on this one field, so it is tested for absence and not
  // for truthiness.
  if (changes.scheduledFor !== undefined)
    body.scheduled_for = changes.scheduledFor;
  if (changes.programmeId !== undefined)
    body.programme_id = changes.programmeId;
  if (changes.cohortId !== undefined) body.cohort_id = changes.cohortId;

  return platformRequest<Sitting>(
    `${org(slug)}/sittings/${encodeURIComponent(sittingId)}`,
    {
      method: "PUT",
      body,
    },
  );
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
  /** Minutes after the sitting's start that this rotation begins; left out keeps what the circuit has. */
  startOffsetMinutes?: number;
  /** Station version id to assessor user id; left out keeps what the circuit has, `{}` clears them. */
  stationAssessors?: Record<string, string>;
}

/**
 * The clock, in the builder's words.
 *
 * `breaks` are 1-based station numbers the break falls *after*, `breakMinutes`
 * is the default length and `breakLengths` the length of any break that differs,
 * keyed by that station number. `sittings/domain.py` drops them outside exam mode and clamps them
 * inside it; `domains/assess/timing.ts` mirrors that so the form only offers
 * answers the server will keep.
 */
export interface CircuitTiming {
  readingMinutes: number;
  simulationMinutes: number;
  breakMinutes: number;
  breaks: number[];
  breakLengths: Record<number, number>;
}

/** `breakLengths` as the api's `break_lengths` list. */
export function breakLengthsBody(lengths: Record<number, number>) {
  return Object.entries(lengths).map(([after, minutes]) => ({
    after_station: Number(after),
    minutes,
  }));
}

/** The api's `break_lengths` list as `breakLengths`. */
export function breakLengthsFrom(
  list: readonly { after_station: number; minutes: number }[] | undefined,
): Record<number, number> {
  return Object.fromEntries(
    (list ?? []).map((entry) => [entry.after_station, entry.minutes]),
  );
}

/** The clock in the wire's words, shared by every circuit write. */
export function timingBody(timing: CircuitTiming) {
  return {
    reading_minutes: timing.readingMinutes,
    simulation_minutes: timing.simulationMinutes,
    break_minutes: timing.breakMinutes,
    breaks: timing.breaks,
    break_lengths: breakLengthsBody(timing.breakLengths),
  };
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
        timing: timingBody(input.timing),
        start_offset_minutes: input.startOffsetMinutes,
        station_assessors: input.stationAssessors,
      },
    },
  );
}

/** Body of POST .../circuits/bulk; `timing` is built with `timingBody`. */
export type CreateExamCircuits = components["schemas"]["CreateExamCircuits"];

/** One exam circuit per candidate, same stations, lead and clock; all are made or none. */
export function createExamCircuits(
  slug: string,
  sittingId: string,
  input: CreateExamCircuits,
): Promise<Circuit[]> {
  return platformRequest<Circuit[]>(
    `${org(slug)}/sittings/${encodeURIComponent(sittingId)}/circuits/bulk`,
    {
      method: "POST",
      body: input,
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
  revision?: number,
): Promise<Circuit> {
  return platformRequest<Circuit>(
    `${org(slug)}/circuits/${encodeURIComponent(circuitId)}`,
    {
      method: "PUT",
      body: {
        revision,
        name: input.name,
        station_version_ids: input.stationVersionIds,
        trainee_ids: input.traineeIds,
        supervisor_user_id: input.supervisorUserId,
        timing: timingBody(input.timing),
        start_offset_minutes: input.startOffsetMinutes,
        station_assessors: input.stationAssessors,
      },
    },
  );
}

/**
 * Call off a sitting nobody has sat. The row is kept as `cancelled`, never
 * deleted. Refused with `sitting_locked` (409) once any circuit has started:
 * those circuits are ended instead.
 */
export function cancelSitting(
  slug: string,
  sittingId: string,
): Promise<Sitting> {
  return platformRequest<Sitting>(
    `${org(slug)}/sittings/${encodeURIComponent(sittingId)}/cancel`,
    {
      method: "POST",
    },
  );
}

/**
 * Remove a circuit set up by mistake. Refused with `circuit_locked` (409) once it
 * has started, because then it holds a record of what was sat.
 */
export function deleteCircuit(slug: string, circuitId: string): Promise<void> {
  return platformRequest<void>(
    `${org(slug)}/circuits/${encodeURIComponent(circuitId)}`,
    {
      method: "DELETE",
    },
  );
}

/* ---------- marking ---------- */

export type SlotReview = components["schemas"]["SlotReviewRead"];
/** What queueing a marking again answered. Declared by hand until schema.d.ts is regenerated (R-5). */
export type RetryMarkingResult = {
  queued: boolean;
  policy_version: string;
  reason: string | null;
};

/** Queue this slot's automatic marking again after it failed. Twice is once. */
export function retrySlotMarking(
  slug: string,
  slotId: string,
): Promise<RetryMarkingResult> {
  return platformRequest<RetryMarkingResult>(
    `${org(slug)}/slots/${encodeURIComponent(slotId)}/marking/retry`,
    {
      method: "POST",
      body: {},
    },
  );
}
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
/** This examiner's own review of a slot, or `null` for none yet. */
export function readMySlotReview(
  slug: string,
  slotId: string,
  signal?: AbortSignal,
): Promise<SlotReview | null> {
  return platformRequest<SlotReview | null>(
    `${org(slug)}/slots/${encodeURIComponent(slotId)}/reviews/mine`,
    { signal },
  );
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
  input: {
    fieldValues: Record<string, unknown>;
    /** Left out by a live tick, which must not overwrite notes typed elsewhere. */
    notes?: string | null;
    status: "draft" | "completed";
    /** A live tick: merge these ratings into the draft and keep the rest as it is. */
    partial?: boolean;
  },
): Promise<SlotReview> {
  return platformRequest<SlotReview>(
    `${org(slug)}/slots/${encodeURIComponent(slotId)}/reviews/mine`,
    {
      method: "PUT",
      body: {
        field_values: input.fieldValues,
        notes: input.notes,
        status: input.status,
        partial: input.partial,
      },
    },
  );
}

/** Take back a draft review, so a stale one stops blocking sign-off. */
export function withdrawReview(
  slug: string,
  slotId: string,
  reviewId: string,
): Promise<void> {
  return platformRequest<void>(
    `${org(slug)}/slots/${encodeURIComponent(slotId)}/reviews/${encodeURIComponent(reviewId)}`,
    { method: "DELETE" },
  );
}

export type ScimToken = components["schemas"]["ScimTokenRead"];
export type ScimTokenIssued = components["schemas"]["ScimTokenIssued"];

/** The identity-provider connectors that may provision this organisation's people. */
export function listScimTokens(
  slug: string,
  signal?: AbortSignal,
): Promise<ScimToken[]> {
  return platformRequest<ScimToken[]>(`${org(slug)}/scim/tokens`, { signal });
}

/** The token itself comes back once, in this response, and is never readable again. */
export function issueScimToken(
  slug: string,
  label: string,
): Promise<ScimTokenIssued> {
  return platformRequest<ScimTokenIssued>(`${org(slug)}/scim/tokens`, {
    method: "POST",
    body: { label },
  });
}

export function revokeScimToken(slug: string, tokenId: string): Promise<void> {
  return platformRequest<void>(
    `${org(slug)}/scim/tokens/${encodeURIComponent(tokenId)}`,
    { method: "DELETE" },
  );
}

export type Invoice = components["schemas"]["InvoiceRead"];
export type InvoiceLine = components["schemas"]["InvoiceLineRead"];
export type InvoicePage = components["schemas"]["Page_InvoiceRead_"];

/** The invoices raised for this organisation, most recently issued first. Org admin only. */
export function listInvoices(
  slug: string,
  signal?: AbortSignal,
  page?: { cursor?: string | null },
): Promise<InvoicePage> {
  return platformRequest<InvoicePage>(`${org(slug)}/invoices`, {
    signal,
    query: { limit: 25, cursor: page?.cursor ?? undefined },
  });
}

/** One invoice with its lines. */
export function readInvoice(slug: string, invoiceId: string, signal?: AbortSignal): Promise<Invoice> {
  return platformRequest<Invoice>(`${org(slug)}/invoices/${encodeURIComponent(invoiceId)}`, { signal });
}

/** Quote the organisation's purchase order number; the api refuses it once the invoice is paid or void. */
export function setInvoicePoNumber(slug: string, invoiceId: string, poNumber: string): Promise<Invoice> {
  return platformRequest<Invoice>(`${org(slug)}/invoices/${encodeURIComponent(invoiceId)}/po-number`, {
    method: "PUT",
    body: { po_number: poNumber },
  });
}
