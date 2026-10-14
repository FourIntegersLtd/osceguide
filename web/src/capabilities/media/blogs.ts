import { PILOT_EXAMS } from "@/foundation/attribution/partnerConstants";
import { bodyMarkdown, type MediaItem } from "@/capabilities/media/api";
import { excerpt } from "@/capabilities/media/support/text";

/** How many articles one page of the blogs index holds, on the server and on "load more". */
export const BLOG_PAGE_SIZE = 24;

/** The api's page cap, used to walk every post for the sitemap. */
export const SITEMAP_PAGE_SIZE = 100;

export interface BlogTab {
  /** `null` is every article. */
  code: string | null;
  label: string;
}

/** `?exam=` as the api takes it: trimmed, lower case, null for none. The server seed and the client load must agree. */
export function normaliseExamQuery(exam: string | undefined): string | null {
  return exam?.trim().toLowerCase() || null;
}

/** One article's public address. */
export function blogPath(slug: string): string {
  return `/blogs/${slug}`;
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
