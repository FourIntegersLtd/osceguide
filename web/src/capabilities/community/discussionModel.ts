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

export type CommunityCategory = "general" | "platform" | "skills" | "exam";

/** What a question is filed under; its specialty tags are subtags of it. */
export const COMMUNITY_CATEGORIES: { id: CommunityCategory; label: string }[] = [
  { id: "general", label: "General" },
  { id: "platform", label: "Platform" },
  { id: "skills", label: "Skills" },
  { id: "exam", label: "Exam" },
];

/** The exam a new question names: only an exam question has one. */
export function composerExamCode(category: CommunityCategory, examCode: string | null): string | null {
  return category === "exam" ? examCode : null;
}

/** The exam the composer starts on: the current one, else the only one this person holds. */
export function defaultExamChoice(codes: readonly string[], current: string | null): string | null {
  if (current) return current;
  return codes.length === 1 ? (codes[0] ?? null) : null;
}

/** What the list asks the server for on a tab: the Exam tab is the exam category for the current exam. */
export function listFilterFor(
  tab: CommunityTab,
  examCode: string | null,
): { category?: CommunityCategory; examCode?: string | null } {
  return tab === "exam" ? { category: "exam", examCode } : {};
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
