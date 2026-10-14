"use client";

import Link from "next/link";
import { HiOutlineChevronLeft } from "react-icons/hi2";
import { productTokens as t } from "@/foundation/ui";
import { bodyMarkdown, contentUpdatedAt, type MediaItem } from "@/capabilities/media/api";
import { Prose } from "@/capabilities/media/Prose";
import { formatPublished, leadsWithHeading, readMinutes } from "@/capabilities/media/support/text";
import { STUDY_KIND_LABEL, studyListPath } from "@/capabilities/media/studyPaths";

/**
 * An article, as the public `/blogs/<slug>` page shows it: a back link to the
 * blogs, a mono meta line, a title, an optional subtitle and the body. `bodyHtml`
 * is the body rendered on the server, so the article is in the first HTML.
 */
export function ArticleView({ item, bodyHtml }: { item: MediaItem; bodyHtml?: string }) {
  const body = bodyMarkdown(item);
  const published = formatPublished(item.published_at);
  const updatedRaw = contentUpdatedAt(item);
  const updated = updatedRaw ? formatPublished(updatedRaw) : null;

  return (
    <div className="mx-auto w-full max-w-[1000px] text-left">
      <Link href={studyListPath("blog")} className="inline-flex items-center gap-1 text-osce-body font-medium text-b2c-text-muted hover:text-osce-ink-900">
        <HiOutlineChevronLeft className="h-3.5 w-3.5" aria-hidden />
        {STUDY_KIND_LABEL.blog}
      </Link>

      <article className="mt-4">
        <header>
          <p className={t.b2cMonoEyebrow}>
            Article
            {item.published_at ? (
              <>
                <span aria-hidden> · </span>
                <time dateTime={item.published_at}>{published}</time>
              </>
            ) : null}
            {body ? <span> · {readMinutes(body)} min read</span> : null}
          </p>

          {!body || !leadsWithHeading(body) ? (
            <h1 className="mt-2 font-title text-osce-display-sm font-semibold text-osce-ink-900">{item.title}</h1>
          ) : null}

          {item.summary?.trim() ? (
            <p className="mt-3 text-osce-body text-b2c-text-muted">{item.summary}</p>
          ) : null}

          {updated && updated !== published ? (
            <p className="mt-2 text-osce-meta text-b2c-text-muted">Updated {updated}</p>
          ) : null}
        </header>

        <div className="mt-6 text-[17px] leading-7 [&_h2]:mt-10 [&_h3]:mt-8 [&_p]:mb-5 [&_p]:text-[17px] [&_p]:leading-7">
          {body ? (
            <Prose content={body} html={bodyHtml} />
          ) : (
            <p className="text-osce-body text-b2c-text-muted">This article has no content yet.</p>
          )}
        </div>
      </article>
    </div>
  );
}
