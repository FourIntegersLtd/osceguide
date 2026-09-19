import { platformRequest, type components } from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";

export type Slot = components["schemas"]["app__features__marketplace__schemas__PostRead"];
export type SlotPage = components["schemas"]["app__core__pagination__Page_PostRead___1"];
export type QueueStatus = components["schemas"]["QueueStatus"];
export type PeerSession = components["schemas"]["PeerSessionRead"];

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
 */

/* ---------- the marketplace ---------- */

export function listSlots(
  params: { examCode?: string | null; cursor?: string | null },
  signal?: AbortSignal,
): Promise<SlotPage> {
  return platformRequest<SlotPage>("/api/v1/marketplace/slots", {
    query: { exam_code: params.examCode ?? undefined, cursor: params.cursor ?? undefined },
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
 * Claim a slot.
 *
 * The row is locked before it is examined, so two people pressing at the same
 * moment serialise and the second is told it is gone — rather than both
 * believing they won.
 */
export function claimSlot(postId: string): Promise<Slot> {
  return platformRequest<Slot>(`/api/v1/marketplace/slots/${encodeURIComponent(postId)}/claim`, {
    method: "POST",
  });
}

export function withdrawSlot(postId: string): Promise<void> {
  return platformRequest<void>(`/api/v1/marketplace/slots/${encodeURIComponent(postId)}`, {
    method: "DELETE",
  });
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

export function leaveQueue(entryId: string): Promise<void> {
  return platformRequest<void>(`/api/v1/peer-practice/queue/${encodeURIComponent(entryId)}`, {
    method: "DELETE",
  });
}

export function listMyPeerSessions(signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_PeerSessionRead_"]>(
    "/api/v1/me/peer-sessions",
    { signal },
  );
}

export function joinPeerSession(sessionId: string): Promise<RoomGrant> {
  return platformRequest<RoomGrant>(
    `/api/v1/me/peer-sessions/${encodeURIComponent(sessionId)}/join`,
    { method: "POST" },
  );
}
