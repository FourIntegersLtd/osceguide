"use client";

import { studyItemHref } from "@/capabilities/media/studyPaths";
import type { ReactNode } from "react";
import Link from "next/link";
import { HiOutlineArrowRight, HiOutlineNewspaper } from "react-icons/hi2";
import { B2CEmptyState, ButtonLink, cn, productTokens as t } from "@/foundation/ui";
import { bodyMarkdown, type MediaItem } from "@/capabilities/media/api";
import { excerpt, formatPublished, readMinutes } from "@/capabilities/media/support/text";
import { b2cCard } from "@/foundation/ui/productTokens";

/** An article has no picture, so its card leads with a block in one of the reading tones, in turn. */
const CARD_TONES = [
  { panel: "bg-osce-tone-history-header text-osce-tone-history-text", dot: "bg-osce-tone-history-border" },
  { panel: "bg-osce-tone-education-header text-osce-tone-education-text", dot: "bg-osce-tone-education-border" },
  { panel: "bg-osce-tone-reasoning-header text-osce-tone-reasoning-text", dot: "bg-osce-tone-reasoning-border" },
];

/** Soft circles and a large icon stand in for a cover image. */
function ToneCover({ tone, className, children }: { tone: number; className?: string; children?: ReactNode }) {
  const t = CARD_TONES[tone % CARD_TONES.length] ?? CARD_TONES[0]!;
  return (
    <span className={cn("relative block overflow-hidden", t.panel, className)} aria-hidden>
      <span className={cn("absolute -right-6 -top-8 h-28 w-28 rounded-full opacity-70", t.dot)} />
      <span className={cn("absolute -bottom-10 left-6 h-24 w-24 rounded-full opacity-50", t.dot)} />
      <HiOutlineNewspaper className="absolute bottom-3 right-4 h-12 w-12 opacity-60" />
      {children}
    </span>
  );
}

export function ArticlesLibrary({
  items,
  hrefFor,
}: {
  items: MediaItem[];
  hrefFor: (path: string) => string;
}) {
  // The server hands these back newest-published-first (`sort=published`), so
  // the first item is the featured one and the rest are the timeline as-is.
  const sorted = items;

  if (sorted.length === 0) {
    return (
      <B2CEmptyState
        icon={HiOutlineNewspaper}
        title="No articles found"
        description="New articles are published regularly, so check back soon."
      />
    );
  }

  const featured = sorted[0];
  if (!featured) return null;
  const rest = sorted.slice(1);

  const featuredBody = bodyMarkdown(featured);
  const featuredBlurb =
    featured.summary?.trim() ||
    (featuredBody ? excerpt(featuredBody, 200) : "Read the latest from the study team.");

  return (
    <div className="space-y-6 pb-4">
      <section className={cn(b2cCard, "grid grid-cols-1 overflow-hidden md:grid-cols-[1fr_280px]")}>
        <div className="flex flex-col gap-2 p-6 md:p-8">
          <p className={t.b2cMonoEyebrow}>Latest · {articleMeta(featured) || "New"}</p>
          <h2 className="text-balance text-osce-title font-semibold text-osce-ink-900">{featured.title}</h2>
          <p className="line-clamp-3 max-w-[640px] text-osce-body text-b2c-text-muted">{featuredBlurb}</p>
          <div className="mt-3">
            <ButtonLink href={studyItemHref(hrefFor, "blog", featured.slug)} variant="primary" size="md">
              Read article
            </ButtonLink>
          </div>
        </div>
        <ToneCover tone={0} className="hidden min-h-[200px] md:block" />
      </section>

      {rest.length > 0 ? (
        <section>
          <h2 className={cn(t.b2cMonoEyebrow, "px-1 pb-2")}>More to read</h2>
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {rest.map((article, position) => (
              <li key={article.id}>
                <Link
                  href={studyItemHref(hrefFor, "blog", article.slug)}
                  className={cn(
                    b2cCard,
                    "group flex h-full flex-col overflow-hidden transition-all hover:-translate-y-0.5 hover:border-osce-ink-400 hover:shadow-md",
                  )}
                >
                  <span className="flex flex-1 flex-col p-5">
                    <span className="flex items-center justify-between gap-2">
                      <span
                        className={cn(
                          "inline-flex h-9 w-9 items-center justify-center rounded-osce-md",
                          CARD_TONES[(position + 1) % CARD_TONES.length]?.panel,
                        )}
                      >
                        <HiOutlineNewspaper className="h-4.5 w-4.5" aria-hidden />
                      </span>
                      <span className="rounded-full bg-b2c-surface-muted px-2.5 py-1 text-osce-meta text-b2c-text-muted">
                        {readLabel(article)}
                      </span>
                    </span>
                    <h3 className="mt-4 line-clamp-2 text-osce-subheading font-semibold text-osce-ink-900">
                      {article.title}
                    </h3>
                    <p className="mt-1.5 line-clamp-3 text-osce-body text-b2c-text-muted">{blurbFor(article)}</p>
                    <span className="mt-auto flex items-center justify-between border-t border-b2c-border-light pt-3 text-osce-meta">
                      <span className="text-b2c-text-muted">{publishedLabel(article)}</span>
                      <span className="flex items-center gap-1 font-medium text-osce-ink-900">
                        Read
                        <HiOutlineArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                      </span>
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function blurbFor(article: MediaItem): string {
  const body = bodyMarkdown(article);
  return article.summary?.trim() || (body ? excerpt(body, 140) : "");
}

function readLabel(article: MediaItem): string {
  const body = bodyMarkdown(article);
  return body ? `${readMinutes(body)} min read` : "Article";
}

function publishedLabel(article: MediaItem): string {
  return article.published_at ? formatPublished(article.published_at, { day: "numeric", month: "short", year: "numeric" }) : "";
}

/** "12 Sep · 4 min read", whichever halves the article has. */
function articleMeta(article: MediaItem): string {
  const body = bodyMarkdown(article);
  return [
    article.published_at ? formatPublished(article.published_at, { day: "numeric", month: "short" }) : null,
    body ? `${readMinutes(body)} min read` : null,
  ]
    .filter(Boolean)
    .join(" · ");
}
