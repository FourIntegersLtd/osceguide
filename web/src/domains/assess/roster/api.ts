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
import { platformRequest, type components } from "@/foundation/platform-client";
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

/**
 * A spreadsheet's worth of trainees in one request.
 *
 * The browser parses the file and the API takes rows, so an import is an
 * ordinary JSON call rather than a multipart upload the server re-parses.
 * Duplicates come back in `skipped` rather than failing the batch, which is
 * what makes a half-recognised file useful instead of a mystery.
 */
export function bulkAddTrainees(slug: string, rows: TraineeInput[]): Promise<BulkTraineesResult> {
  return platformRequest<BulkTraineesResult>(`${orgPath(slug)}/trainees/bulk`, {
    method: "POST",
    body: { trainees: rows.map(traineeBody) },
  });
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

/** Everything granted, revoked rows included: `live` is the field that gates. */
export function listEntitlements(slug: string, signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_EntitlementRead_"]>(
    `${orgPath(slug)}/entitlements`,
    { signal },
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
