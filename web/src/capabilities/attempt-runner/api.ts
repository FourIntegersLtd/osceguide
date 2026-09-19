import { platformRequest, type components } from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";

export type Attempt = components["schemas"]["AttemptRead"];
export type AssessmentResult = components["schemas"]["AssessmentResultRead"];
export type Transcript = components["schemas"]["TranscriptRead"];

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

/** Mint the room token. `voice` decides Cloud or self-hosted; the browser never does. */
export function attemptVoiceToken(attemptId: string, signal?: AbortSignal): Promise<RoomGrant> {
  return platformRequest<RoomGrant>(
    `/api/v1/attempts/${encodeURIComponent(attemptId)}/voice-token`,
    { method: "POST", signal },
  );
}

/** Give up on an attempt that was never really run. */
export function abandonAttempt(attemptId: string): Promise<void> {
  return platformRequest<void>(`/api/v1/attempts/${encodeURIComponent(attemptId)}/abandon`, {
    method: "POST",
  });
}

export function readResult(attemptId: string, signal?: AbortSignal): Promise<AssessmentResult> {
  return platformRequest<AssessmentResult>(
    `/api/v1/attempts/${encodeURIComponent(attemptId)}/result`,
    { signal },
  );
}

export function readTranscript(attemptId: string, signal?: AbortSignal): Promise<Transcript> {
  return platformRequest<Transcript>(
    `/api/v1/attempts/${encodeURIComponent(attemptId)}/transcript`,
    { signal },
  );
}
