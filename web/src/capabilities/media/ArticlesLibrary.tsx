"use client";

import Link from "next/link";
import { HiOutlineNewspaper } from "react-icons/hi2";
import { B2CEmptyState, ButtonLink, cn, productTokens as t } from "@/foundation/ui";
import { bodyMarkdown, type MediaItem } from "@/capabilities/media/api";
import { excerpt, formatPublished, readMinutes } from "@/capabilities/media/support/text";
import { B2CHero } from "@/foundation/ui/B2CHero";
import { b2cCard } from "@/foundation/ui/productTokens";

/** An article has no picture, so its card leads with a block in one of the reading tones, in turn. */
const CARD_TONES = ["bg-osce-tone-history-bg", "bg-osce-tone-education-bg", "bg-osce-tone-reasoning-bg"];

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
      <B2CHero
        eyebrow="Latest"
        title={featured.title}
        action={
          <ButtonLink href={hrefFor(`/library/${featured.slug}`)} variant="primary" size="md">
            Read article
          </ButtonLink>
        }
      >
        <span className="line-clamp-3">{featuredBlurb}</span>
      </B2CHero>

      {rest.length > 0 ? (
        <section>
          <h2 className={cn(t.b2cMonoEyebrow, "px-1 pb-2")}>More to read</h2>
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {rest.map((article, position) => (
              <li key={article.id}>
                <Link
                  href={hrefFor(`/library/${article.slug}`)}
                  className={cn(b2cCard, "flex h-full flex-col p-3.5 transition-colors hover:border-osce-ink-400")}
                >
                  <span
                    className={cn("mb-3 block h-[140px] rounded-[10px]", CARD_TONES[position % CARD_TONES.length])}
                    aria-hidden
                  />
                  <h3 className="line-clamp-2 text-osce-subheading font-semibold text-osce-ink-900">{article.title}</h3>
                  <p className="mt-1 text-osce-meta text-b2c-text-muted">{articleMeta(article)}</p>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
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
