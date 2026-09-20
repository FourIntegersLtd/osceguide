"use client";

import Link from "next/link";
import { HiOutlineCalendar, HiOutlineClock } from "react-icons/hi2";
import { B2CPanelCard, B2CPanelCardBody, cn, productTokens as t } from "@/foundation/ui";
import { bodyMarkdown, contentUpdatedAt, type MediaItem } from "@/capabilities/media/api";
import { Prose } from "@/capabilities/media/Prose";
import { formatPublished, leadsWithHeading, readMinutes } from "@/capabilities/media/support/text";
import { STUDY_KIND_LABEL, studyListPath } from "@/capabilities/media/studyPaths";

/**
 * An article.
 *
 * The retiring client rendered these in the marketing skin, because the blog
 * was a marketing page that happened to be reachable from the app. Inside the
 * library it is the app's own reading surface — same header, same meta line,
 * same "back to everything" at both ends, painted in the vocabulary of the
 * shell it is actually mounted in.
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
  const backLink = (
    <Link href={hrefFor(studyListPath("blog"))} className={cn("inline-block", t.b2cLink)}>
      ← {STUDY_KIND_LABEL.blog}
    </Link>
  );

  return (
    <div className={cn("w-full text-left", t.b2cProseMeasureWide)}>
      {backLink}

      <article className="mt-7">
        <header className="border-b border-b2c-border pb-6">
          <p className={t.b2cEyebrow}>
            {item.published_at ? <time dateTime={item.published_at}>{published}</time> : null}
            {item.published_at && body ? <span aria-hidden> · </span> : null}
            {body ? `${readMinutes(body)} min read` : null}
          </p>

          {!body || !leadsWithHeading(body) ? (
            <h1 className={cn("mt-3", t.b2cPageTitle)}>{item.title}</h1>
          ) : null}

          {published || updated ? (
            <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-osce-meta text-b2c-text-muted">
              {published ? (
                <span className="flex items-center gap-1.5">
                  <HiOutlineCalendar aria-hidden /> Published {published}
                </span>
              ) : null}
              {updated ? (
                <span className="flex items-center gap-1.5">
                  <HiOutlineClock aria-hidden /> Updated {updated}
                </span>
              ) : null}
            </div>
          ) : null}
        </header>

        <div className="mt-8">
          {body ? (
            <Prose content={body} />
          ) : (
            <B2CPanelCard className="mt-0">
              <B2CPanelCardBody>
                <p className={t.b2cBodyTextMuted}>This article has no content yet.</p>
              </B2CPanelCardBody>
            </B2CPanelCard>
          )}
        </div>
      </article>

      <div className="mt-12 border-t border-b2c-border pt-6">{backLink}</div>
    </div>
  );
}
