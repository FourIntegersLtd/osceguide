import { PILOT_EXAMS } from "@/foundation/attribution/partnerConstants";
import { bodyMarkdown, type MediaItem } from "@/capabilities/media/api";
import { excerpt } from "@/capabilities/media/support/text";

export interface BlogTab {
  /** `null` is every article. */
  code: string | null;
  label: string;
}

/** The public blogs page, optionally narrowed to one exam. */
export function blogsHref(examCode: string | null): string {
  return examCode ? `/blogs?exam=${encodeURIComponent(examCode)}` : "/blogs";
}

/** "All", then one tab per exam the platform runs. The exam list itself is behind sign-in, and this page is not. */
export const BLOG_EXAM_TABS: readonly BlogTab[] = [
  { code: null, label: "All" },
  ...PILOT_EXAMS.map((code) => ({ code, label: code.toUpperCase() })),
];

/** The card text under an article's title: its summary, else the start of its body. */
export function articleBlurb(item: MediaItem, max: number): string {
  const body = bodyMarkdown(item);
  return item.summary?.trim() || (body ? excerpt(body, max) : "");
}
