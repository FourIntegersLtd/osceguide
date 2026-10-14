import { platformRequest, type components } from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";

export type Slot = components["schemas"]["app__features__marketplace__schemas__PostRead"];
export type SlotPage = components["schemas"]["app__core__pagination__Page_PostRead___1"];
export type QueueStatus = components["schemas"]["QueueStatus"];
export type PeerSession = components["schemas"]["PeerSessionRead"];
export type PeerSessionPage = components["schemas"]["Page_PeerSessionRead_"];
export type PracticeSession = components["schemas"]["PracticeSessionRead"];
export type PracticeFeedbackInput = components["schemas"]["SessionFeedback"];
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

export const MARKETPLACE_PAGE_SIZE = 100;

/**
 * One page of the marketplace, ordered by the server.
 *
 * `status` narrows to what is still open (`available`) or already booked
 * (`claimed`); `when` narrows to `upcoming` or `past`. The retiring client's
 * unpaginated posts list walked every page for one exam and sorted them in
 * the browser into Available / Scheduled / Completed — the server does both
 * jobs now, one section at a time.
 */
export function listSlots(
  params: {
    cursor?: string | null;
    orgId?: string | null;
    examCode?: string | null;
    status?: Exclude<Slot["status"], "cancelled"> | null;
    when?: "upcoming" | "past" | null;
    limit?: number;
  },
  signal?: AbortSignal,
): Promise<SlotPage> {
  return platformRequest<SlotPage>("/api/v1/marketplace/slots", {
    query: {
      cursor: params.cursor ?? undefined,
      limit: params.limit ?? undefined,
      exam_code: params.examCode ?? undefined,
      status: params.status ?? undefined,
      when: params.when ?? undefined,
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

export function listMyPosts(signal?: AbortSignal): Promise<SlotPage> {
  return platformRequest<SlotPage>("/api/v1/me/marketplace/posts", { signal });
}

/** One page of this person's booked sessions; `when: "upcoming"` is the server's own definition, not a client-side clock read. */
export function listMyPeerSessions(
  params: { cursor?: string | null; limit?: number; when?: "upcoming" | "past" | null } = {},
  signal?: AbortSignal,
): Promise<PeerSessionPage> {
  return platformRequest<PeerSessionPage>("/api/v1/me/peer-sessions", {
    query: {
      cursor: params.cursor ?? undefined,
      limit: params.limit ?? undefined,
      when: params.when ?? undefined,
    },
    signal,
  });
}

/**
 * Open from twenty minutes before the appointed hour until an hour after;
 * `peer_session_not_open` outside that, or once the session is cancelled.
 */
export function joinPeerSession(sessionId: string): Promise<PeerSession> {
  return platformRequest<PeerSession>(
    `/api/v1/me/peer-sessions/${encodeURIComponent(sessionId)}/join`,
    { method: "POST" },
  );
}

export function cancelPeerSession(sessionId: string): Promise<void> {
  return platformRequest<void>(
    `/api/v1/me/peer-sessions/${encodeURIComponent(sessionId)}/cancel`,
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

export function practiceSessionStreamPath(sessionId: string): string {
  return `/api/v1/me/practice-sessions/${encodeURIComponent(sessionId)}/stream`;
}

export function recordPracticePresence(sessionId: string): Promise<PracticeSession> {
  return platformRequest<PracticeSession>(
    `/api/v1/me/practice-sessions/${encodeURIComponent(sessionId)}/presence`,
    { method: "POST" },
  );
}

/**
 * The rating one partner gives the other. `rating` is optional and
 * `would_practice_again` required, as the retiring form asked them.
 */
export function submitPracticeFeedback(
  sessionId: string,
  input: PracticeFeedbackInput,
): Promise<PracticeSession> {
  return platformRequest<PracticeSession>(
    `/api/v1/me/practice-sessions/${encodeURIComponent(sessionId)}/feedback`,
    { method: "POST", body: input },
  );
}

/**
 * Answering the match. A pair is matched into a session that waits for both
 * to accept; `partner_unavailable` when the other person has already gone.
 */
export function acceptPracticeMatch(sessionId: string): Promise<PracticeSession> {
  return platformRequest<PracticeSession>(
    `/api/v1/me/practice-sessions/${encodeURIComponent(sessionId)}/accept`,
    { method: "POST" },
  );
}

export function declinePracticeMatch(sessionId: string): Promise<PracticeSession> {
  return platformRequest<PracticeSession>(
    `/api/v1/me/practice-sessions/${encodeURIComponent(sessionId)}/decline`,
    { method: "POST" },
  );
}

export function reportPracticeAbuse(sessionId: string, message: string): Promise<void> {
  return platformRequest<void>(
    `/api/v1/me/practice-sessions/${encodeURIComponent(sessionId)}/report-abuse`,
    { method: "POST", body: { message } },
  );
}

export function reportPracticeNoShow(sessionId: string, message?: string | null): Promise<void> {
  return platformRequest<void>(
    `/api/v1/me/practice-sessions/${encodeURIComponent(sessionId)}/report-no-show`,
    { method: "POST", body: { message: message ?? null } },
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
