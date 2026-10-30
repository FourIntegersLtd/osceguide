"use client";

import Link from "next/link";
import { FiArrowRight } from "react-icons/fi";
import { studyTabPathForSlug } from "@/capabilities/media/studyPaths";
import { articleBlurb } from "@/capabilities/media/blogs";
import { bodyMarkdown, type MediaItem } from "@/capabilities/media/api";
import { formatPublished, readMinutes } from "@/capabilities/media/support/text";

/** "12 Sep 2026 · 4 min read", whichever halves the article has. */
function articleMeta(article: MediaItem): string {
  const body = bodyMarkdown(article);
  return [
    article.published_at ? formatPublished(article.published_at, { day: "numeric", month: "short", year: "numeric" }) : null,
    body ? `${readMinutes(body)} min read` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}

/** The public blogs index: one responsive grid of cards on the site tokens, newest first as the server sends them. */
export function ArticlesLibrary({ items }: { items: MediaItem[] }) {
  if (items.length === 0) {
    return (
      <div className="rounded-2xl border border-site-line bg-site-card p-8 text-center">
        <b className="block text-lg text-site-ink">No articles found</b>
        <p className="mt-1 text-site-body">New articles are published regularly, so check back soon.</p>
      </div>
    );
  }

  return (
    <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((article) => (
        <li key={article.id} className="min-w-0">
          <Link
            href={studyTabPathForSlug("blog", article.slug)}
            className="group flex h-full flex-col rounded-2xl border border-site-line bg-site-card p-6 transition-colors hover:border-site-brand"
          >
            <span className="font-landing-mono text-[11px] font-medium uppercase tracking-[0.13em] text-site-faint">
              {articleMeta(article) || "Article"}
            </span>
            <h2 className="mt-3 text-balance break-words font-landing-heading text-xl font-bold leading-snug text-site-ink">
              {article.title}
            </h2>
            <p className="mt-2 line-clamp-3 text-site-body">{articleBlurb(article, 160)}</p>
            <span className="mt-auto inline-flex min-h-11 items-center gap-1.5 pt-4 font-semibold text-site-brand">
              Read article
              <FiArrowRight aria-hidden className="transition-transform group-hover:translate-x-0.5" />
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
