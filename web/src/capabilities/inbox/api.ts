import { platformRequest } from "@/foundation/platform-client";
import type { components } from "@/foundation/platform-client/schema";

export type InboxMessage = components["schemas"]["InboxMessageRead"];
export type InboxPage = components["schemas"]["Page_InboxMessageRead_"];

const ME = "/api/v1/me/messages";

/** My messages and the announcements posted since I joined, newest first. */
export function listMyMessages(
  query: { cursor?: string | null; limit?: number } = {},
  signal?: AbortSignal,
): Promise<InboxPage> {
  return platformRequest<InboxPage>(ME, {
    signal,
    query: { cursor: query.cursor ?? undefined, limit: query.limit ?? 25 },
  });
}

export async function readUnreadCount(signal?: AbortSignal): Promise<number> {
  const result = await platformRequest<components["schemas"]["InboxUnreadCount"]>(`${ME}/unread-count`, { signal });
  return result.count;
}

export function markMessageRead(messageId: string): Promise<void> {
  return platformRequest<void>(`${ME}/${encodeURIComponent(messageId)}/read`, { method: "POST" });
}

export function markAllRead(): Promise<void> {
  return platformRequest<void>(`${ME}/read-all`, { method: "POST" });
}
