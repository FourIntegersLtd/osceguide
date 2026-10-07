/**
 * The roster: the people an organisation examines.
 *
 * `trainee_id` in this slice is `trainees.id`. It is *not* what a circuit
 * takes — a slot names a `users.id`, because an organisation may examine
 * somebody it has never rostered. So `resolveRoster` answers roster ids, and
 * anything that goes on to build a circuit must carry `Trainee.user_id`
 * across instead. Both spellings are live in the same API and the schema is
 * the only place that says which is which.
 */
import { PlatformError, platformRequest, type components } from "@/foundation/platform-client";
import {
  collectPages,
  orgPath,
  pageQuery,
  type PageParams,
  type Trainee,
  type TraineePage,
} from "@/domains/assess/api";

export type Cohort = components["schemas"]["CohortRead"];
export type TraineeGroup = components["schemas"]["GroupRead"];
export type BulkTraineesResult = components["schemas"]["BulkTraineesResult"];
export type SkippedTrainee = components["schemas"]["SkippedTrainee"];
export type ResolvedRoster = components["schemas"]["ResolvedRoster"];
export type Entitlement = components["schemas"]["EntitlementRead"];
export type Exam = components["schemas"]["ExamRead"];
export type Invitation = components["schemas"]["InvitationRead"];

export function listTrainees(
  slug: string,
  signal?: AbortSignal,
  page?: PageParams,
): Promise<TraineePage> {
  return platformRequest<TraineePage>(`${orgPath(slug)}/trainees`, {
    signal,
    query: pageQuery(page),
  });
}

/** The whole roster, cursors walked: the group editor needs all of it. */
export function listAllTrainees(slug: string, signal?: AbortSignal): Promise<Trainee[]> {
  return collectPages((cursor) => listTrainees(slug, signal, { cursor }));
}

export interface TraineeInput {
  email: string;
  firstName: string | null;
  lastName: string | null;
  cohortId: string | null;
}

function traineeBody(input: TraineeInput) {
  return {
    email: input.email,
    first_name: input.firstName,
    last_name: input.lastName,
    cohort_id: input.cohortId,
  };
}

/** An address with no account is invited and linked in the same call. */
export function addTrainee(slug: string, input: TraineeInput): Promise<Trainee> {
  return platformRequest<Trainee>(`${orgPath(slug)}/trainees`, {
    method: "POST",
    body: traineeBody(input),
  });
}

/** Rows one import request takes; the server refuses more (`too_many_trainees`). */
// Must stay within MAX_BULK_TRAINEES in api/app/features/roster/schemas.py, the server limit.
export const IMPORT_CHUNK = 500;

/**
 * A spreadsheet's worth of trainees, sent `IMPORT_CHUNK` rows at a time and
 * answered as one result.
 *
 * The browser parses the file and the API takes rows, so an import is an
 * ordinary JSON call rather than a multipart upload the server re-parses.
 * Duplicates come back in `skipped` rather than failing the batch, which is
 * what makes a half-recognised file useful instead of a mystery. A chunk that
 * is refused stops the import: its rows and every later one come back in
 * `skipped` under the refusal's code, so the rows already added still read as
 * added. A refusal before anything was added is thrown.
 */
export async function bulkAddTrainees(slug: string, rows: TraineeInput[]): Promise<BulkTraineesResult> {
  const created: Trainee[] = [];
  const skipped: NonNullable<BulkTraineesResult["skipped"]> = [];
  for (let start = 0; start < rows.length; start += IMPORT_CHUNK) {
    try {
      const part = await platformRequest<BulkTraineesResult>(`${orgPath(slug)}/trainees/bulk`, {
        method: "POST",
        body: { trainees: rows.slice(start, start + IMPORT_CHUNK).map(traineeBody) },
      });
      created.push(...(part.created ?? []));
      skipped.push(...(part.skipped ?? []));
    } catch (cause) {
      if (start === 0) throw cause;
      const code = cause instanceof PlatformError ? cause.code : "import_failed";
      skipped.push(...rows.slice(start).map((row) => ({ email: row.email, code })));
      break;
    }
  }
  return { created, skipped };
}

/**
 * Revoke or restore a trainee's access — one route for both, because they are
 * the same decision and two routes invite one of them to be forgotten.
 */
export function setTraineeAccess(
  slug: string,
  traineeId: string,
  revoked: boolean,
): Promise<Trainee> {
  return platformRequest<Trainee>(
    `${orgPath(slug)}/trainees/${encodeURIComponent(traineeId)}/access`,
    { method: "POST", body: { revoked } },
  );
}

/**
 * Remove a roster row nobody ever examined.
 *
 * Refused (`trainee_in_use`, 409) the moment a decision exists — revoking
 * access is what stays on the roster with their results intact; this is only
 * for a row added by mistake, or one who left before anything ran.
 */
export function deleteTrainee(slug: string, traineeId: string): Promise<void> {
  return platformRequest<void>(`${orgPath(slug)}/trainees/${encodeURIComponent(traineeId)}`, {
    method: "DELETE",
  });
}

/**
 * GDPR erasure for a row `deleteTrainee` refuses (`trainee_in_use`): the
 * address and name are scrubbed, any decision recorded about them stays.
 * Idempotent — calling this twice is a no-op that still answers 200.
 */
export function anonymiseTrainee(slug: string, traineeId: string): Promise<Trainee> {
  return platformRequest<Trainee>(
    `${orgPath(slug)}/trainees/${encodeURIComponent(traineeId)}/anonymise`,
    { method: "POST" },
  );
}

/**
 * What the roster edit sheet may correct about somebody already on it.
 *
 * The address is deliberately absent: it identifies the entry inside the
 * organisation and is what the account link was made against, so changing it
 * re-points a person's results rather than fixing a typo. Group membership is
 * absent too — a group is a row of its own, written by `setGroupMembers`.
 */
export interface TraineeEdit {
  firstName: string | null;
  lastName: string | null;
  cohortId: string | null;
}

/**
 * Correct a roster entry.
 *
 * PATCH with partial semantics: a key left out is one the server must not
 * touch, and an explicit null is a clear. So a form may send all three only
 * when it rendered all three — which the edit dialog does — and the `undefined`
 * case is for a caller that edits one field on its own.
 */
export function updateTrainee(
  slug: string,
  traineeId: string,
  edit: Partial<TraineeEdit>,
): Promise<Trainee> {
  const body: components["schemas"]["UpdateTrainee"] = {};
  if (edit.firstName !== undefined) body.first_name = edit.firstName;
  if (edit.lastName !== undefined) body.last_name = edit.lastName;
  if (edit.cohortId !== undefined) body.cohort_id = edit.cohortId;
  return platformRequest<Trainee>(
    `${orgPath(slug)}/trainees/${encodeURIComponent(traineeId)}`,
    { method: "PATCH", body },
  );
}

/**
 * Send the choose-a-password link again.
 *
 * An institution rosters people by address long before they sign in and the one
 * email can be lost; with no button the candidate sits unexamined while the
 * organisation believes it told them. The answer is the address and the
 * institution — never the token, which goes only to the person it was minted
 * for.
 *
 * The backend answers `invitation_not_pending` (409) when the person has
 * already chosen a password: mailing a set-password link to somebody who can
 * sign in is an invitation to take over their account. Branch on the code.
 */
export function resendInvitation(slug: string, traineeId: string): Promise<Invitation> {
  return platformRequest<Invitation>(
    `${orgPath(slug)}/trainees/${encodeURIComponent(traineeId)}/resend-invitation`,
    { method: "POST" },
  );
}

export function listCohorts(slug: string, signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_CohortRead_"]>(`${orgPath(slug)}/cohorts`, {
    signal,
  });
}

export function addCohort(
  slug: string,
  input: { name: string; academicYear: string | null },
): Promise<Cohort> {
  return platformRequest<Cohort>(`${orgPath(slug)}/cohorts`, {
    method: "POST",
    body: { name: input.name, academic_year: input.academicYear },
  });
}

/**
 * Rename an intake, or say which academic year it belongs to.
 *
 * Which exams a cohort is bound to is not here: the roster row carries no such
 * column, so a field for it would promise a write that goes nowhere.
 */
export function renameCohort(
  slug: string,
  cohortId: string,
  input: { name?: string; academicYear?: string | null },
): Promise<Cohort> {
  const body: components["schemas"]["UpdateCohort"] = {};
  if (input.name !== undefined) body.name = input.name;
  if (input.academicYear !== undefined) body.academic_year = input.academicYear;
  return platformRequest<Cohort>(
    `${orgPath(slug)}/cohorts/${encodeURIComponent(cohortId)}`,
    { method: "PATCH", body },
  );
}

/**
 * Remove an intake.
 *
 * Refused with `cohort_in_use` (409) while trainees still belong to it: a
 * silent clear would read as those people having never had an intake, so the
 * screen must say so and let the administrator move them first.
 */
export function deleteCohort(slug: string, cohortId: string): Promise<void> {
  return platformRequest<void>(`${orgPath(slug)}/cohorts/${encodeURIComponent(cohortId)}`, {
    method: "DELETE",
  });
}

export function listTraineeGroups(slug: string, signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_GroupRead_"]>(
    `${orgPath(slug)}/trainee-groups`,
    { signal },
  );
}

export function addTraineeGroup(slug: string, label: string): Promise<TraineeGroup> {
  return platformRequest<TraineeGroup>(`${orgPath(slug)}/trainee-groups`, {
    method: "POST",
    body: { label },
  });
}

/**
 * Rename a group. Its members stay — that is the rule this whole slice exists
 * to hold, where the retiring client matched a copied label and a rename
 * emptied the group out from under everybody in it.
 */
export function renameGroup(slug: string, groupId: string, label: string): Promise<TraineeGroup> {
  return platformRequest<TraineeGroup>(
    `${orgPath(slug)}/trainee-groups/${encodeURIComponent(groupId)}`,
    { method: "PATCH", body: { label } satisfies components["schemas"]["UpdateGroup"] },
  );
}

/**
 * Remove a group.
 *
 * Refused with `group_not_empty` (409) while anybody is in it — the membership,
 * and anything addressed to the group, would go with it, so the emptied list is
 * stated first rather than discovered afterwards.
 */
export function deleteGroup(slug: string, groupId: string): Promise<void> {
  return platformRequest<void>(
    `${orgPath(slug)}/trainee-groups/${encodeURIComponent(groupId)}`,
    { method: "DELETE" },
  );
}

/**
 * Who is in a group, by trainee id.
 *
 * `GET …/members` pages the group's own membership. It used to be read by
 * resolving the roster for the group, which answers who a circuit would
 * contain rather than who is in the group.
 */
export async function readGroupMembers(
  slug: string,
  groupId: string,
  signal?: AbortSignal,
): Promise<string[]> {
  const members = await collectPages((cursor) =>
    platformRequest<TraineePage>(
      `${orgPath(slug)}/trainee-groups/${encodeURIComponent(groupId)}/members`,
      { signal, query: pageQuery({ cursor }) },
    ),
  );
  return members.map((trainee) => trainee.id);
}

/**
 * PUT, not POST: the body states who is in the group, so membership is set
 * rather than appended to and two administrators editing at once cannot each
 * contribute half of it.
 */
export function setGroupMembers(
  slug: string,
  groupId: string,
  traineeIds: string[],
): Promise<TraineeGroup> {
  return platformRequest<TraineeGroup>(
    `${orgPath(slug)}/trainee-groups/${encodeURIComponent(groupId)}/members`,
    { method: "PUT", body: { trainee_ids: traineeIds } },
  );
}

/**
 * Preview who a circuit would contain, groups expanded.
 *
 * A POST because it takes a body, not because it changes anything. It warns
 * about a linked group that is empty, which is the whole point of asking
 * before the examination rather than during it.
 */
export function resolveRoster(
  slug: string,
  input: { traineeIds?: string[]; groupIds?: string[] },
): Promise<ResolvedRoster> {
  return platformRequest<ResolvedRoster>(`${orgPath(slug)}/roster/resolve`, {
    method: "POST",
    body: { trainee_ids: input.traineeIds ?? [], group_ids: input.groupIds ?? [] },
  });
}

/* ------------------------------------------------------------------------
 * Entitlements: an organisation's people practising between sittings.
 *
 * An exam-day slot never needs one — a dispatched slot skips the gate. This
 * is for the practice a trainee does in between, which otherwise runs out
 * with the consumer free trial.
 * --------------------------------------------------------------------- */

/**
 * Everything granted, revoked rows included: `live` is the field that gates.
 *
 * One server page at a time, searched in SQL: an institution's grants can
 * outgrow "load it all and filter in the browser" the same way its roster
 * can.
 */
export function listEntitlements(
  slug: string,
  signal?: AbortSignal,
  page?: PageParams,
): Promise<components["schemas"]["Page_EntitlementRead_"]> {
  return platformRequest<components["schemas"]["Page_EntitlementRead_"]>(
    `${orgPath(slug)}/entitlements`,
    { signal, query: pageQuery(page) },
  );
}

/** By email: the grant is against the person's account, not the roster row. */
export function grantEntitlement(
  slug: string,
  input: { email: string; examCode: string; endsAt: string | null },
): Promise<Entitlement> {
  return platformRequest<Entitlement>(`${orgPath(slug)}/entitlements`, {
    method: "POST",
    body: { email: input.email, exam_code: input.examCode, ends_at: input.endsAt },
  });
}

export function revokeEntitlement(slug: string, entitlementId: string): Promise<void> {
  return platformRequest<void>(
    `${orgPath(slug)}/entitlements/${encodeURIComponent(entitlementId)}/revoke`,
    { method: "POST" },
  );
}

/** This institution's own exams, plus the platform catalogue. */
export function listExams(slug: string, signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_ExamRead_"]>(`${orgPath(slug)}/exams`, {
    signal,
  });
}
