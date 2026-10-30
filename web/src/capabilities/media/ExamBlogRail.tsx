"use client";

import Link from "next/link";
import { useAsync } from "@/foundation/hooks";
import { listMedia } from "@/capabilities/media/api";
import { articleBlurb, blogsHref } from "@/capabilities/media/blogs";
import { studyTabPathForSlug } from "@/capabilities/media/studyPaths";

const RAIL = 3;

/**
 * A small rail of one exam's articles for its public landing page. Nothing
 * published, or a failed read, shows nothing rather than a hole in the page.
 */
export function ExamBlogRail({ examCode }: { examCode: string }) {
  const state = useAsync(
    (signal) =>
      listMedia({ kind: "blog", examCode, limit: RAIL, sort: "published" }, signal).then((page) => page.items),
    [examCode],
  );
  // A failed read has no data: the rail simply is not drawn.
  const articles = state.data ?? [];
  if (articles.length === 0) return null;

  return (
    <section aria-label={`${examCode.toUpperCase()} articles`} className="mx-auto w-full max-w-[1000px] px-4 py-12 sm:px-6">
      <div className="flex items-end justify-between gap-4">
        <h2 className="font-landing-heading text-2xl font-bold text-site-ink">
          {examCode.toUpperCase()} articles
        </h2>
        <Link href={blogsHref(examCode)} className="font-semibold text-site-brand underline underline-offset-4">
          All {examCode.toUpperCase()} articles
        </Link>
      </div>
      <ul className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
        {articles.map((article) => (
          <li key={article.id}>
            <Link
              href={studyTabPathForSlug("blog", article.slug)}
              className="block h-full rounded-xl border border-site-line p-5 hover:border-site-brand"
            >
              <h3 className="line-clamp-2 font-landing-heading text-lg font-bold text-site-ink">{article.title}</h3>
              <p className="mt-1.5 line-clamp-3 text-site-body">{articleBlurb(article, 140)}</p>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
