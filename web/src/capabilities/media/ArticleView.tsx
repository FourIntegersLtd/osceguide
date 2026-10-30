"use client";

import Link from "next/link";
import { FiChevronLeft } from "react-icons/fi";
import { Eyebrow } from "@/foundation/ui";
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
    <div className="mx-auto w-full max-w-[70ch] text-left">
      <Link href={studyListPath("blog")} className="inline-flex min-h-11 items-center gap-1 font-medium text-site-muted hover:text-site-brand">
        <FiChevronLeft aria-hidden />
        {STUDY_KIND_LABEL.blog}
      </Link>

      <article className="mt-4">
        <header>
          <p className="text-site-brand">
            <Eyebrow>Article</Eyebrow>
            <span className="font-landing-mono text-[11px] uppercase tracking-[0.13em] text-site-faint">
              {item.published_at ? (
                <>
                  <span aria-hidden> · </span>
                  <time dateTime={item.published_at}>{published}</time>
                </>
              ) : null}
              {body ? <span> · {readMinutes(body)} min read</span> : null}
            </span>
          </p>

          {!body || !leadsWithHeading(body) ? (
            <h1 className="mt-3 break-words font-landing-heading text-3xl font-bold leading-tight tracking-tight text-site-ink sm:text-4xl">{item.title}</h1>
          ) : null}

          {item.summary?.trim() ? (
            <p className="mt-4 text-lg leading-relaxed text-site-body">{item.summary}</p>
          ) : null}

          {updated && updated !== published ? (
            <p className="mt-2 text-sm text-site-muted">Updated {updated}</p>
          ) : null}
        </header>

        <div
          className={[
            "mt-8 min-w-0 break-words text-[17px] leading-7 text-site-body [&_h2]:mt-10 [&_h3]:mt-8 [&_p]:mb-5 [&_p]:text-[17px] [&_p]:leading-7",
            "[&_h1]:text-site-ink [&_h2]:text-site-ink [&_h3]:text-site-ink [&_h4]:text-site-ink [&_strong]:text-site-ink",
            "[&_p]:text-site-body [&_li]:text-site-body [&_td]:text-site-body [&_th]:text-site-ink",
            "[&_a]:text-site-brand [&_a]:underline [&_a]:underline-offset-2 [&_img]:h-auto [&_img]:max-w-full [&_pre]:overflow-x-auto [&_table]:block [&_table]:overflow-x-auto",
          ].join(" ")}
        >
          {body ? (
            <Prose content={body} html={bodyHtml} />
          ) : (
            <p className="text-site-muted">This article has no content yet.</p>
          )}
        </div>
      </article>
    </div>
  );
}
