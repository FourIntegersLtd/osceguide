"use client";

import Link from "next/link";
import { useAsync } from "@/foundation/hooks";
import { listMedia } from "@/capabilities/media/api";
import { blogsHref, examBlogs } from "@/capabilities/media/blogs";
import { excerpt } from "@/capabilities/media/support/text";
import { bodyMarkdown } from "@/capabilities/media/api";
import { studyItemHref } from "@/capabilities/media/studyPaths";

const RAIL = 3;

/**
 * A small rail of one exam's articles for its public landing page. Nothing
 * published, or a failed read, shows nothing rather than a hole in the page.
 */
export function ExamBlogRail({ examCode }: { examCode: string }) {
  const state = useAsync(
    (signal) =>
      listMedia({ kind: "blog", examCode, limit: 12, sort: "published" }, signal)
        .then((page) => examBlogs(page.items, examCode, RAIL)),
    [examCode],
  );
  // A failed read has no data: the rail simply is not drawn.
  const articles = state.data ?? [];
  if (articles.length === 0) return null;

  return (
    <section aria-label={`${examCode.toUpperCase()} articles`} className="mx-auto w-full max-w-[1000px] px-4 py-12 sm:px-6">
      <div className="flex items-end justify-between gap-4">
        <h2 className="font-title text-osce-heading font-semibold text-osce-ink-900">
          {examCode.toUpperCase()} articles
        </h2>
        <Link href={blogsHref(examCode)} className="text-osce-body font-medium text-osce-ink-900 underline">
          All {examCode.toUpperCase()} articles
        </Link>
      </div>
      <ul className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {articles.map((article) => {
          const body = bodyMarkdown(article);
          return (
            <li key={article.id}>
              <Link
                href={studyItemHref((path) => path, "blog", article.slug)}
                className="block h-full rounded-osce-md border border-osce-border p-5 hover:border-osce-ink-400"
              >
                <h3 className="line-clamp-2 text-osce-subheading font-semibold text-osce-ink-900">{article.title}</h3>
                <p className="mt-1.5 line-clamp-3 text-osce-body text-osce-ink-600">
                  {article.summary?.trim() || (body ? excerpt(body, 140) : "")}
                </p>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
