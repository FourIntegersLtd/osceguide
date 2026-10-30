"use client";

import Link from "next/link";
import { AsyncBoundary, Eyebrow, LoadMore, cn } from "@/foundation/ui";
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
    <div className="mx-auto w-full max-w-[1200px] px-4 py-12 sm:px-6 sm:py-16">
      <p>
        <Eyebrow>Blogs</Eyebrow>
      </p>
      <h1 className="mt-3 max-w-3xl font-landing-heading text-3xl font-bold leading-tight tracking-tight text-site-ink sm:text-5xl">
        Guidance and updates from the study team
      </h1>
      <p className="mt-4 max-w-2xl text-lg leading-relaxed text-site-body">
        Practical advice for your exam, written by the OSCE Guide study team.
      </p>
      <nav aria-label="Filter by exam" className="mt-8 flex flex-wrap gap-2">
        {BLOG_EXAM_TABS.map((tab) => (
          <Link
            key={tab.label}
            href={blogsHref(tab.code)}
            aria-current={tab.code === examCode ? "page" : undefined}
            className={cn(
              "inline-flex min-h-11 items-center rounded-full border px-4 text-sm font-semibold transition-colors",
              tab.code === examCode
                ? "border-site-brand bg-site-brand text-site-on-brand"
                : "border-site-rule bg-site-card text-site-body hover:border-site-brand hover:text-site-brand",
            )}
          >
            {tab.label}
          </Link>
        ))}
      </nav>
      <div className="mt-10">
        <AsyncBoundary state={pages.state}>
          {(items) => (
            <>
              <ArticlesLibrary items={items} />
              <LoadMore hasMore={pages.hasMore} busy={pages.loadingMore} onLoad={pages.loadMore} error={pages.moreError} />
            </>
          )}
        </AsyncBoundary>
      </div>
    </div>
  );
}
