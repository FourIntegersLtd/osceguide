"use client";

import Link from "next/link";
import { HiOutlineArrowRight, HiOutlineNewspaper } from "react-icons/hi2";
import {
  B2CEmptyState,
  cn,
  productTokens as t,
} from "@/foundation/ui";
import { bodyMarkdown, type MediaItem } from "@/capabilities/media/api";
import { excerpt, formatPublished, readMinutes } from "@/capabilities/media/support/text";

function dateStack(iso: string | null | undefined): { month: string; day: string } {
  const formatted = formatPublished(iso, { month: "short" });
  const day = formatPublished(iso, { day: "numeric" });
  const month = formatted.replace(/\s+\d+$/, "").trim();
  return { month, day };
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
  const timeline = rest;

  const featuredBody = bodyMarkdown(featured);
  const featuredBlurb =
    featured.summary?.trim() ||
    (featuredBody ? excerpt(featuredBody, 200) : "Read the latest from the study team.");

  return (
    <div className="space-y-10 pb-4">
      <section
        className={cn(
          "relative overflow-hidden rounded-2xl border border-b2c-border",
          "bg-gradient-to-br from-b2c-surface-muted via-osce-surface to-b2c-surface-muted",
          "px-6 py-8 sm:px-10 sm:py-12",
        )}
      >
        <p className={t.b2cEyebrow}>
          {featured.published_at ? (
            <time dateTime={featured.published_at}>{formatPublished(featured.published_at)}</time>
          ) : (
            "Latest"
          )}
          {featuredBody ? (
            <>
              <span aria-hidden> · </span>
              {readMinutes(featuredBody)} min read
            </>
          ) : null}
        </p>
        <h2 className={cn("mt-3 max-w-2xl text-balance", t.b2cPageTitle)}>{featured.title}</h2>
        <p className={cn("mt-4 max-w-2xl line-clamp-3", t.b2cBodyTextMuted)}>{featuredBlurb}</p>
        <Link
          href={hrefFor(`/library/${featured.slug}`)}
          className={cn(t.b2cButtonPrimary, "mt-8 inline-flex items-center gap-2")}
        >
          Read article
          <HiOutlineArrowRight className="h-4 w-4" aria-hidden />
        </Link>
      </section>

      {rest.length > 0 ? (
        <section>
          <h3 className={cn(t.b2cSectionTitle, "mb-4")}>More to read</h3>
          <ul className="divide-y divide-b2c-border rounded-xl border border-b2c-border bg-osce-surface">
            {timeline.map((article) => {
              const body = bodyMarkdown(article);
              const { month, day } = dateStack(article.published_at);
              return (
                <li key={article.id}>
                  <Link
                    href={hrefFor(`/library/${article.slug}`)}
                    className="group flex gap-4 px-4 py-5 transition-colors hover:bg-b2c-surface-muted sm:gap-6 sm:px-6"
                  >
                    <div className="flex w-14 shrink-0 flex-col items-center justify-center rounded-lg bg-b2c-surface-muted py-2 text-center">
                      <span className="text-[10px] font-semibold uppercase tracking-wide text-osce-ink-400">
                        {month}
                      </span>
                      <span className="text-lg font-semibold tabular-nums text-osce-ink-900">{day}</span>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className={cn(t.b2cPanelListRowTitle, "group-hover:text-osce-accent")}>
                        {article.title}
                      </p>
                      <p className={cn(t.b2cPanelCardMeta, "mt-1 line-clamp-2")}>
                        {article.summary?.trim() ||
                          (body ? excerpt(body, 120) : formatPublished(article.published_at))}
                      </p>
                    </div>
                    <HiOutlineArrowRight
                      className="mt-1 h-4 w-4 shrink-0 text-b2c-text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-osce-accent"
                      aria-hidden
                    />
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
