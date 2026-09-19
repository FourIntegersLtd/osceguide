import { platformRequest, type components } from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";

export type Slot = components["schemas"]["app__features__marketplace__schemas__PostRead"];
export type SlotPage = components["schemas"]["app__core__pagination__Page_PostRead___1"];
export type QueueStatus = components["schemas"]["QueueStatus"];
export type PeerSession = components["schemas"]["PeerSessionRead"];
export type PeerSessionPage = components["schemas"]["Page_PeerSessionRead_"];
export type PracticeSession = components["schemas"]["PracticeSessionRead"];
export type PracticeSessionPage = components["schemas"]["Page_PracticeSessionRead_"];

/**
 * Practising with another person, two ways.
 *
 * **The marketplace** is planned: somebody posts a time they are free and
 * somebody else claims it. **The queue** is immediate: you wait and are paired
 * with whoever is also waiting.
 *
 * Both carry an `audience`, so an institution can scope either to its own
 * cohort. That is why they are a capability rather than a consumer feature —
 * mounting them on Assess is a word in `capability.ts`, not a port.
 *
 * The two halves are two aggregates on the backend and stay two here: a
 * marketplace claim makes a `PeerSession` at an appointed hour, and the queue
 * makes a `PracticeSession` the moment two people are matched. Collapsing them
 * in the browser would mean guessing which set of routes answers for an id.
 */

/* ---------- the marketplace ---------- */

export function listSlots(
  params: { cursor?: string | null; orgId?: string | null },
  signal?: AbortSignal,
): Promise<SlotPage> {
  return platformRequest<SlotPage>("/api/v1/marketplace/slots", {
    query: {
      cursor: params.cursor ?? undefined,
      visibility: params.orgId ? "organisation" : undefined,
      audience_org_id: params.orgId ?? undefined,
    },
    signal,
  });
}

export function offerSlot(input: {
  examCode: string;
  startsAt: string;
  durationMinutes: number;
  note: string | null;
  orgId?: string | null;
}): Promise<Slot> {
  return platformRequest<Slot>("/api/v1/marketplace/slots", {
    method: "POST",
    body: {
      exam_code: input.examCode,
      starts_at: input.startsAt,
      duration_minutes: input.durationMinutes,
      note: input.note,
      audience: { visibility: input.orgId ? "organisation" : "public", org_id: input.orgId ?? null },
    },
  });
}

/**
 * Claim a slot, which is what makes the session.
 *
 * The row is locked before it is examined, so two people pressing at the same
 * moment serialise and the second is told it is gone — rather than both
 * believing they won. That is why the answer is the session and not the slot.
 */
export function claimSlot(postId: string): Promise<PeerSession> {
  return platformRequest<PeerSession>(
    `/api/v1/marketplace/slots/${encodeURIComponent(postId)}/claim`,
    { method: "POST" },
  );
}

export function withdrawSlot(postId: string): Promise<void> {
  return platformRequest<void>(`/api/v1/marketplace/slots/${encodeURIComponent(postId)}`, {
    method: "DELETE",
  });
}

export function listMyPeerSessions(signal?: AbortSignal): Promise<PeerSessionPage> {
  return platformRequest<PeerSessionPage>("/api/v1/me/peer-sessions", { signal });
}

/** Open ten minutes before the appointed hour; `peer_session_not_open` before that. */
export function joinPeerSession(sessionId: string): Promise<PeerSession> {
  return platformRequest<PeerSession>(
    `/api/v1/me/peer-sessions/${encodeURIComponent(sessionId)}/join`,
    { method: "POST" },
  );
}

/* ---------- the queue ---------- */

export function joinQueue(examCode: string, orgId?: string | null): Promise<QueueStatus> {
  return platformRequest<QueueStatus>("/api/v1/peer-practice/queue", {
    method: "POST",
    body: {
      exam_code: examCode,
      audience: { visibility: orgId ? "organisation" : "public", org_id: orgId ?? null },
    },
  });
}

export function readQueueStatus(entryId: string, signal?: AbortSignal): Promise<QueueStatus> {
  return platformRequest<QueueStatus>(
    `/api/v1/peer-practice/queue/${encodeURIComponent(entryId)}`,
    { signal },
  );
}

/**
 * Where the queue pushes its own state.
 *
 * Not a request: `useEventStream` mints the ticket and opens the source, so
 * this is the one place the path is spelled. The old client polled this every
 * three seconds while somebody sat watching the screen, which is the place in
 * the product where polling cost the most.
 */
export function queueStreamPath(entryId: string): string {
  return `/api/v1/peer-practice/queue/${encodeURIComponent(entryId)}/stream`;
}

export function leaveQueue(entryId: string): Promise<void> {
  return platformRequest<void>(`/api/v1/peer-practice/queue/${encodeURIComponent(entryId)}`, {
    method: "DELETE",
  });
}

/* ---------- the paired session ---------- */

export function listPracticeSessions(signal?: AbortSignal): Promise<PracticeSessionPage> {
  return platformRequest<PracticeSessionPage>("/api/v1/me/practice-sessions", { signal });
}

export function readPracticeSession(
  sessionId: string,
  signal?: AbortSignal,
): Promise<PracticeSession> {
  return platformRequest<PracticeSession>(
    `/api/v1/me/practice-sessions/${encodeURIComponent(sessionId)}`,
    { signal },
  );
}

export function endPracticeSession(
  sessionId: string,
  reason: string | null = null,
): Promise<PracticeSession> {
  return platformRequest<PracticeSession>(
    `/api/v1/me/practice-sessions/${encodeURIComponent(sessionId)}/end`,
    { method: "POST", body: { reason } },
  );
}

/**
 * A way into the room the pair were matched into.
 *
 * The browser never picks a server: the API mints the token and decides Cloud
 * against self-hosted. `practice_session_ended` (409) is the answer for a
 * session somebody already left.
 */
export function practiceVoiceToken(sessionId: string): Promise<RoomGrant> {
  return platformRequest<RoomGrant>(
    `/api/v1/me/practice-sessions/${encodeURIComponent(sessionId)}/voice-token`,
    { method: "POST" },
  );
}
