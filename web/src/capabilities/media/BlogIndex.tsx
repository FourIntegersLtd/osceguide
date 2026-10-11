"use client";

import Link from "next/link";
import { AsyncBoundary, cn } from "@/foundation/ui";
import { useAsync, useCursorPages } from "@/foundation/hooks";
import { listAllMedia, listMedia } from "@/capabilities/media/api";
import { ArticlesLibrary } from "@/capabilities/media/ArticlesLibrary";
import { blogExamTabs } from "@/capabilities/media/blogs";

const PAGE = 24;
const open = (path: string) => path;

/**
 * The public blogs page: every published article, newest first, with a tab per
 * exam. Readable signed out, so it asks the same `GET /media` the landing rail does.
 */
export function BlogIndex({ examCode }: { examCode: string | null }) {
  const everything = useAsync((signal) => listAllMedia("blog", signal), []);
  const pages = useCursorPages(
    (cursor, signal) => listMedia({ kind: "blog", cursor, limit: PAGE, examCode, sort: "published" }, signal),
    [examCode],
  );
  const tabs = blogExamTabs(everything.data ?? []);

  return (
    <main className="mx-auto w-full max-w-[1000px] px-4 py-12 text-left sm:px-6">
      <h1 className="font-title text-osce-display-sm font-semibold text-osce-ink-900">Blogs</h1>
      <p className="mt-2 text-osce-body text-osce-ink-600">Guidance and updates from the study team.</p>
      {tabs.length > 2 ? (
        <nav aria-label="Filter by exam" className="mt-6 flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <Link
              key={tab.label}
              href={tab.href}
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
      ) : null}
      <div className="mt-8">
        <AsyncBoundary state={pages.state}>
          {(items) => (
            <>
              <ArticlesLibrary items={items} hrefFor={open} />
              {pages.hasMore ? (
                <div className="mt-6 flex justify-center">
                  <button
                    type="button"
                    onClick={pages.loadMore}
                    disabled={pages.loadingMore}
                    className="rounded-osce-md border border-osce-border px-4 py-2 text-osce-body font-medium text-osce-ink-900"
                  >
                    {pages.loadingMore ? "Loading…" : "Load more"}
                  </button>
                </div>
              ) : null}
            </>
          )}
        </AsyncBoundary>
      </div>
    </main>
  );
}
