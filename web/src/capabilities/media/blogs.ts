import type { MediaItem } from "@/capabilities/media/api";

export interface BlogTab {
  /** `null` is every article. */
  code: string | null;
  label: string;
  href: string;
}

/** The public blogs page, optionally narrowed to one exam. */
export function blogsHref(examCode: string | null): string {
  return examCode ? `/blogs?exam=${encodeURIComponent(examCode)}` : "/blogs";
}

/** "All", then one tab per exam that has an article, in code order. */
export function blogExamTabs(items: readonly Pick<MediaItem, "exam_code">[]): BlogTab[] {
  const codes = [...new Set(items.flatMap((item) => (item.exam_code ? [item.exam_code] : [])))].sort();
  return [
    { code: null, label: "All", href: blogsHref(null) },
    ...codes.map((code) => ({ code, label: code.toUpperCase(), href: blogsHref(code) })),
  ];
}

/** One exam's own articles, newest first as handed over: the list also carries unexamined ones. */
export function examBlogs(items: readonly MediaItem[], examCode: string, limit: number): MediaItem[] {
  return items.filter((item) => item.exam_code === examCode).slice(0, limit);
}
