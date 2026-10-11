import type { B2CSegmentedTabItem } from "@/foundation/ui";

export type CommunityTab = "all" | "exam" | "questions" | "answers";

export const COMMUNITY_TABS: B2CSegmentedTabItem<CommunityTab>[] = [
  { id: "all", label: "All" },
  { id: "exam", label: "Exam" },
  { id: "questions", label: "My questions" },
  { id: "answers", label: "My answers" },
];

/** The `?tab=` value, or All when it is missing or not one of ours. */
export function parseTab(value: string | null): CommunityTab {
  return COMMUNITY_TABS.find((tab) => tab.id === value)?.id ?? "all";
}

/** The query string for a tab; `compose` opens the composer on it. */
export function tabHref(tab: CommunityTab, options: { compose?: boolean } = {}): string {
  return `?tab=${tab}${options.compose ? "&compose=1" : ""}`;
}

export type ReplyOrder = "newest" | "oldest";

/** A sorted copy. The thread is unpaged, so ordering it here is complete. */
export function sortReplies<T extends { created_at: string }>(replies: readonly T[], order: ReplyOrder): T[] {
  const sign = order === "newest" ? -1 : 1;
  return [...replies].sort((a, b) => sign * (Date.parse(a.created_at) - Date.parse(b.created_at)));
}

/**
 * What the list asks the server for on a tab: the Exam tab is the current exam's questions, any
 * category. `null` when that tab has no exam to narrow by: it must show nothing, not every question.
 */
export function listFilterFor(tab: CommunityTab, examCode: string | null): { examCode?: string } | null {
  if (tab !== "exam") return {};
  return examCode ? { examCode } : null;
}

/** Shown in place of a name on a reply the assistant wrote: Athena signs it. */
export const ASSISTANT_LABEL = "Athena";

/**
 * `@somebody`, or the assistant's label. The name is joined by the backend; a deleted account has
 * none and reads as a colleague, never as a uuid.
 */
export function authorLabel(
  post: { author_id: string | null; author_name: string | null; is_assistant: boolean },
  viewerId: string | null,
  viewerName: string,
): string {
  if (post.is_assistant) return ASSISTANT_LABEL;
  if (post.author_id === viewerId) return `@${viewerName}`;
  const name = post.author_name?.trim();
  return name ? `@${name}` : "@a colleague";
}
