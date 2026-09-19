import { platformRequest, type components } from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";

export type OrgDashboard = components["schemas"]["OrgDashboard"];
export type Sitting = components["schemas"]["SittingRead"];
export type SittingPage = components["schemas"]["Page_SittingRead_"];
export type MySittings = components["schemas"]["MySittings"];
export type MySitting = components["schemas"]["MySitting"];
export type Trainee = components["schemas"]["TraineeRead"];

const org = (slug: string) => `/api/v1/orgs/${encodeURIComponent(slug)}`;

export function readOrgDashboard(slug: string, signal?: AbortSignal): Promise<OrgDashboard> {
  return platformRequest<OrgDashboard>(`${org(slug)}/dashboard`, { signal });
}

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
export type FeedbackTemplate = components["schemas"]["FeedbackTemplateRead"];

export function listProgrammes(slug: string, signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_ProgrammeRead_"]>(
    `${org(slug)}/programmes`,
    { signal },
  );
}

export function listFeedbackTemplates(slug: string, signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_FeedbackTemplateRead_"]>(
    `${org(slug)}/feedback-templates`,
    { signal },
  );
}

export function listTemplateVersions(slug: string, templateId: string, signal?: AbortSignal) {
  return platformRequest<components["schemas"]["FeedbackTemplateVersionRead"][]>(
    `${org(slug)}/feedback-templates/${encodeURIComponent(templateId)}/versions`,
    { signal },
  );
}

/** A sitting cannot exist without a published feedback template bound to it. */
export function createSitting(
  slug: string,
  input: {
    name: string;
    mode: "training" | "exam";
    programmeId: string | null;
    feedbackTemplateVersionId: string;
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
      feedback_template_version_id: input.feedbackTemplateVersionId,
      scheduled_for: input.scheduledFor,
    },
  });
}

export type Circuit = components["schemas"]["CircuitRead"];

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
  input: {
    name: string;
    stationVersionIds: string[];
    traineeIds: string[];
    supervisorUserId: string | null;
    timing: { readingMinutes: number; simulationMinutes: number };
  },
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
        },
      },
    },
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

/* ---------- results ---------- */

export type TraineeResult = components["schemas"]["TraineeResultRead"];

export function readMyResult(sittingId: string, signal?: AbortSignal): Promise<TraineeResult> {
  return platformRequest<TraineeResult>(
    `/api/v1/me/results/${encodeURIComponent(sittingId)}`,
    { signal },
  );
}

export function acknowledgeResult(sittingId: string): Promise<void> {
  return platformRequest<void>(
    `/api/v1/me/results/${encodeURIComponent(sittingId)}/acknowledge`,
    { method: "POST" },
  );
}

/* ---------- the trainee's side ---------- */

export function readMySittings(signal?: AbortSignal): Promise<MySittings> {
  return platformRequest<MySittings>("/api/v1/me/sittings", { signal });
}

/** Join the room for the circuit I am rostered onto. */
export function joinCircuit(circuitId: string, signal?: AbortSignal): Promise<RoomGrant> {
  return platformRequest<RoomGrant>(
    `/api/v1/me/circuits/${encodeURIComponent(circuitId)}/join-token`,
    { signal },
  );
}
