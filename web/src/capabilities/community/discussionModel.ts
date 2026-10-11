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
