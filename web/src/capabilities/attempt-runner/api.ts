import { platformRequest, type components } from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";

export type Attempt = components["schemas"]["AttemptRead"];
export type AssessmentResult = components["schemas"]["AssessmentResultRead"];
export type Transcript = components["schemas"]["TranscriptRead"];
export type AttemptBrief = components["schemas"]["AttemptBriefRead"];
export type AttemptReview = components["schemas"]["AttemptReviewRead"];
export type AttemptHistoryItem = components["schemas"]["AttemptHistoryItem"];
export type DoctorInformation = components["schemas"]["DoctorInformationRead"];
export type CandidateScenario = components["schemas"]["CandidateScenarioRead"];
export type ManagementPlan = components["schemas"]["ManagementPlanRead"];
export type PatientReview = components["schemas"]["PatientReviewRead"];
export type StationTeaching = components["schemas"]["StationTeachingRead"];
export type VoiceQueueStanding = components["schemas"]["VoiceQueueStanding"];

/**
 * The kinds of attempt, which are all one row in one table.
 *
 * Consumer practice, a station-set entry, a debrief, institutional
 * self-practice, an exam slot and a peer session differ only in why the person
 * was permitted to start. That is why there is one runner for all of them
 * rather than one per arm, which is what the old clients had.
 */
export type AttemptKind = "practice" | "self_practice" | "set_entry" | "debrief" | "slot" | "peer";

export function createAttempt(
  input: { examCode: string; kind: AttemptKind; stationVersionId?: string | null },
  signal?: AbortSignal,
): Promise<Attempt> {
  return platformRequest<Attempt>("/api/v1/attempts", {
    method: "POST",
    body: {
      exam_code: input.examCode,
      kind: input.kind,
      station_version_id: input.stationVersionId ?? null,
    },
    signal,
    // A double-submitted start is one attempt, not two. The old supervisor
    // console guarded this with a module-level Set, which a reload emptied.
    idempotencyKey: `attempt:${input.examCode}:${input.stationVersionId ?? "none"}:${input.kind}`,
  });
}

export function readAttempt(attemptId: string, signal?: AbortSignal): Promise<Attempt> {
  return platformRequest<Attempt>(`/api/v1/attempts/${encodeURIComponent(attemptId)}`, { signal });
}

/**
 * Mint the room token, or learn the candidate's place in line.
 *
 * `voice` decides Cloud or self-hosted; the browser never does. When every
 * seat is taken it answers 202 with a place instead: a token then would join a
 * room no patient ever enters. Watch `voiceQueuePath` and ask again on `ready`.
 */
export function attemptVoiceToken(
  attemptId: string,
  signal?: AbortSignal,
): Promise<RoomGrant | VoiceQueueStanding> {
  return platformRequest<RoomGrant | VoiceQueueStanding>(
    `/api/v1/attempts/${encodeURIComponent(attemptId)}/voice-token`,
    { method: "POST", signal },
  );
}

/** The candidate's place in line, pushed until a seat is theirs. For `useEventStream`. */
export function voiceQueuePath(attemptId: string): string {
  return `/api/v1/attempts/${encodeURIComponent(attemptId)}/voice-queue`;
}

/** Give up on an attempt that was never really run. */
export function abandonAttempt(attemptId: string): Promise<void> {
  return platformRequest<void>(`/api/v1/attempts/${encodeURIComponent(attemptId)}/abandon`, {
    method: "POST",
  });
}

/**
 * Every marking this attempt has, oldest first.
 *
 * A page, not one result: re-scoring under a new policy writes beside the old
 * one so a candidate's history stays readable. This was typed as a single
 * result and read `.payload` off the page, which is `undefined` — so the
 * institution's slot review and the consumer's feedback screen both rendered
 * an empty marking and neither failed.
 */
export async function readResults(
  attemptId: string,
  signal?: AbortSignal,
): Promise<AssessmentResult[]> {
  const page = await platformRequest<components["schemas"]["Page_AssessmentResultRead_"]>(
    `/api/v1/attempts/${encodeURIComponent(attemptId)}/result`,
    { signal },
  );
  return page.items;
}

/** The marking to show when an attempt has several: the most recent. */
export function latestResult(results: AssessmentResult[]): AssessmentResult | null {
  return results[results.length - 1] ?? null;
}

export function readTranscript(attemptId: string, signal?: AbortSignal): Promise<Transcript> {
  return platformRequest<Transcript>(
    `/api/v1/attempts/${encodeURIComponent(attemptId)}/transcript`,
    { signal },
  );
}

/**
 * The candidate's brief, keyed on the attempt rather than the station.
 *
 * The library's own read carries no content on purpose — browsing is open to
 * everybody and the brief is part of the exam — so this is the only way a
 * candidate sees what is in front of the doctor. Readable from the moment the
 * attempt exists, which is what makes the reading period possible.
 */
export function readAttemptBrief(attemptId: string, signal?: AbortSignal): Promise<AttemptBrief> {
  return platformRequest<AttemptBrief>(
    `/api/v1/attempts/${encodeURIComponent(attemptId)}/brief`,
    { signal },
  );
}

/**
 * The model answer: the patient's ideas and concerns, and the management plan.
 *
 * Refused with `attempt_not_finished` (409) until the consultation is over,
 * because before that it is the answer to the station being sat.
 */
export function readAttemptReview(
  attemptId: string,
  signal?: AbortSignal,
): Promise<AttemptReview> {
  return platformRequest<AttemptReview>(
    `/api/v1/attempts/${encodeURIComponent(attemptId)}/review`,
    { signal },
  );
}

/**
 * What this person has sat, newest first.
 *
 * The listing three screens were doing without: the transcript picker, the
 * feedback history and the practice set's station table all count or list
 * attempts, and the only list that existed was the ten most recent inlined on
 * the dashboard.
 */
export function listMyAttempts(
  params: {
    stationVersionId?: string | null;
    setEntryId?: string | null;
    limit?: number;
    cursor?: string | null;
  } = {},
  signal?: AbortSignal,
): Promise<{ items: AttemptHistoryItem[]; next_cursor?: string | null }> {
  return platformRequest("/api/v1/me/attempts", {
    query: {
      station_version_id: params.stationVersionId ?? undefined,
      set_entry_id: params.setEntryId ?? undefined,
      limit: params.limit,
      cursor: params.cursor ?? undefined,
    },
    signal,
  });
}
