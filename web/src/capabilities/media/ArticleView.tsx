"use client";

import Link from "next/link";
import { HiOutlineChevronLeft } from "react-icons/hi2";
import { productTokens as t } from "@/foundation/ui";
import { bodyMarkdown, contentUpdatedAt, type MediaItem } from "@/capabilities/media/api";
import { Prose } from "@/capabilities/media/Prose";
import { formatPublished, leadsWithHeading, readMinutes } from "@/capabilities/media/support/text";
import { STUDY_KIND_LABEL, studyListPath } from "@/capabilities/media/studyPaths";
import { DiscussWithAthena } from "@/capabilities/help/DiscussWithAthena";

/**
 * An article.
 *
 * The retiring client rendered these in the marketing skin, because the blog
 * was a marketing page that happened to be reachable from the app. Inside the
 * library it is the app's own reading surface: a back link, a mono meta line
 * and the body, painted in the vocabulary of the shell it is mounted in.
 */
export function ArticleView({
  item,
  hrefFor,
}: {
  item: MediaItem;
  hrefFor: (path: string) => string;
}) {
  const body = bodyMarkdown(item);
  const published = formatPublished(item.published_at);
  const updatedRaw = contentUpdatedAt(item);
  const updated = updatedRaw ? formatPublished(updatedRaw) : null;

  return (
    <div className="mx-auto w-full max-w-[1000px] text-left">
      <Link href={hrefFor(studyListPath("blog"))} className="inline-flex items-center gap-1 text-osce-body font-medium text-b2c-text-muted hover:text-osce-ink-900">
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
            <h1 className="mt-2 font-title text-osce-heading font-semibold text-osce-ink-900">{item.title}</h1>
          ) : null}

          {updated && updated !== published ? (
            <p className="mt-2 text-osce-meta text-b2c-text-muted">Updated {updated}</p>
          ) : null}

          <DiscussWithAthena className="mt-4" topic={{ title: item.title, kind: "blog", slug: item.slug }} />
        </header>

        <div className="mt-6 text-[17px] leading-7 [&_p]:text-[17px] [&_p]:leading-7">
          {body ? (
            <Prose content={body} />
          ) : (
            <p className="text-osce-body text-b2c-text-muted">This article has no content yet.</p>
          )}
        </div>
      </article>
    </div>
  );
}
