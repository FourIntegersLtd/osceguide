"use client";

import Link from "next/link";
import { AsyncBoundary, LoadMore, cn } from "@/foundation/ui";
import { useCursorPages } from "@/foundation/hooks";
import { listMedia, type MediaPage } from "@/capabilities/media/api";
import { ArticlesLibrary } from "@/capabilities/media/ArticlesLibrary";
import { BLOG_EXAM_TABS, BLOG_PAGE_SIZE, blogsHref, normaliseExamQuery } from "@/capabilities/media/blogs";

/**
 * The public blogs page: every published article, newest first, with a tab per
 * exam. Readable signed out, so it asks the same `GET /media` the landing rail does.
 */
export function BlogIndex({ examQuery, initialPage }: { examQuery: string | undefined; initialPage?: MediaPage }) {
  const examCode = normaliseExamQuery(examQuery);
  const pages = useCursorPages(
    (cursor, signal) => listMedia({ kind: "blog", cursor, limit: BLOG_PAGE_SIZE, examCode, sort: "published" }, signal),
    [examCode],
    initialPage,
  );

  return (
    <main className="mx-auto w-full max-w-[1000px] px-4 py-12 text-left sm:px-6">
      <h1 className="font-title text-osce-display-sm font-semibold text-osce-ink-900">Blogs</h1>
      <p className="mt-2 text-osce-body text-osce-ink-600">Guidance and updates from the study team.</p>
      <nav aria-label="Filter by exam" className="mt-6 flex flex-wrap gap-2">
          {BLOG_EXAM_TABS.map((tab) => (
            <Link
              key={tab.label}
              href={blogsHref(tab.code)}
              aria-current={tab.code === examCode ? "page" : undefined}
              className={cn(
                "rounded-full border px-3.5 py-1.5 text-osce-meta font-medium",
                tab.code === examCode
                  ? "border-osce-ink-900 bg-osce-ink-900 text-white"
                  : "border-osce-border text-osce-ink-700 hover:border-osce-ink-400",
              )}
            >
              {tab.label}
            </Link>
          ))}
      </nav>
      <div className="mt-8">
        <AsyncBoundary state={pages.state}>
          {(items) => (
            <>
              <ArticlesLibrary items={items} />
              <LoadMore hasMore={pages.hasMore} busy={pages.loadingMore} onLoad={pages.loadMore} error={pages.moreError} />
            </>
          )}
        </AsyncBoundary>
      </div>
    </main>
  );
}
