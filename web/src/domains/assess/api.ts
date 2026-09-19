import { platformRequest, type components } from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";

export type OrgDashboard = components["schemas"]["OrgDashboard"];
export type Sitting = components["schemas"]["SittingRead"];
export type SittingPage = components["schemas"]["Page_SittingRead_"];
export type CircuitConsole = components["schemas"]["CircuitConsole"];
export type ConsoleSlot = components["schemas"]["ConsoleSlot"];
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

export function readConsole(
  slug: string,
  circuitId: string,
  signal?: AbortSignal,
): Promise<CircuitConsole> {
  return platformRequest<CircuitConsole>(
    `${org(slug)}/circuits/${encodeURIComponent(circuitId)}/console`,
    { signal },
  );
}

/**
 * The supervisor's controls.
 *
 * Every one of these is a server-side state transition on the circuit, not a
 * local edit that is later saved. The old console kept the clock in the
 * supervisor's browser and broadcast it over LiveKit packets, so a refresh lost
 * the exam's timing and two supervisors disagreed about it.
 */
export const circuitActions = {
  start: (slug: string, circuitId: string) => act(slug, circuitId, "start"),
  advance: (slug: string, circuitId: string) => act(slug, circuitId, "advance"),
  pause: (slug: string, circuitId: string) => act(slug, circuitId, "pause"),
  resume: (slug: string, circuitId: string) => act(slug, circuitId, "resume"),
  end: (slug: string, circuitId: string) => act(slug, circuitId, "end"),
  resendPatient: (slug: string, circuitId: string) => act(slug, circuitId, "resend-patient"),
  resetClock: (slug: string, circuitId: string) => act(slug, circuitId, "reset-clock"),
};

function act(slug: string, circuitId: string, action: string): Promise<void> {
  return platformRequest<void>(
    `${org(slug)}/circuits/${encodeURIComponent(circuitId)}/${action}`,
    { method: "POST" },
  );
}

export function extendClock(slug: string, circuitId: string, seconds: number): Promise<void> {
  return platformRequest<void>(
    `${org(slug)}/circuits/${encodeURIComponent(circuitId)}/extend-clock`,
    { method: "POST", body: { seconds } },
  );
}

/** A room-admin token, so a supervisor can listen in without publishing. */
export function observerToken(
  slug: string,
  circuitId: string,
  signal?: AbortSignal,
): Promise<RoomGrant> {
  return platformRequest<RoomGrant>(
    `${org(slug)}/circuits/${encodeURIComponent(circuitId)}/observer-token`,
    { method: "POST", signal },
  );
}

export function listTrainees(slug: string, signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_TraineeRead_"]>(`${org(slug)}/trainees`, {
    signal,
  });
}

export function listMemberships(slug: string, signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_MembershipRead_"]>(`${org(slug)}/memberships`, {
    signal,
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

/* ---------- marking ---------- */

export type SlotReview = components["schemas"]["SlotReviewRead"];
export type SlotReviews = components["schemas"]["SlotReviewsRead"];

export function readSlotReviews(
  slug: string,
  slotId: string,
  signal?: AbortSignal,
): Promise<SlotReviews> {
  return platformRequest<SlotReviews>(`${org(slug)}/slots/${encodeURIComponent(slotId)}/reviews`, {
    signal,
  });
}

/** My own review of a slot, which is the one I may edit. */
export function readMyReview(
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

export function recordDecision(
  slug: string,
  sittingId: string,
  traineeId: string,
  input: { assessmentOutcome: string; rationale: string },
) {
  return platformRequest<unknown>(
    `${org(slug)}/sittings/${encodeURIComponent(sittingId)}/candidates/${encodeURIComponent(traineeId)}/decision`,
    { method: "POST", body: { assessment_outcome: input.assessmentOutcome, rationale: input.rationale } },
  );
}

export function signOffDecision(slug: string, sittingId: string, traineeId: string) {
  return platformRequest<unknown>(
    `${org(slug)}/sittings/${encodeURIComponent(sittingId)}/candidates/${encodeURIComponent(traineeId)}/decision/sign-off`,
    { method: "POST" },
  );
}

export function releaseDecision(slug: string, sittingId: string, traineeId: string) {
  return platformRequest<unknown>(
    `${org(slug)}/sittings/${encodeURIComponent(sittingId)}/candidates/${encodeURIComponent(traineeId)}/decision/release`,
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
