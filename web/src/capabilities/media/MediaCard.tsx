"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { HiOutlineArrowRight } from "react-icons/hi2";
import { LuFileText, LuHeadphones, LuNewspaper, LuPresentation } from "react-icons/lu";
import type { IconType } from "react-icons";
import { Badge, cn, productTokens as t } from "@/foundation/ui";
import {
  MEDIA_KIND_LABELS,
  bodyMarkdown,
  deckSlides,
  deckVideoUrl,
  isMediaKind,
  specialtiesOf,
  type MediaItem,
  type MediaKind,
} from "@/capabilities/media/api";
import { excerpt, formatPublished, readMinutes } from "@/capabilities/media/support/text";

export const MEDIA_KIND_ICON: Record<MediaKind, IconType> = {
  slide_deck: LuPresentation,
  summary: LuFileText,
  blog: LuNewspaper,
  podcast: LuHeadphones,
};

export function mediaKindOf(item: { kind: string }): MediaKind | null {
  return isMediaKind(item.kind) ? item.kind : null;
}

/**
 * The line under a card's title.
 *
 * The four kinds had four cards in the retiring client, and the only thing
 * that really differed between them was this line — slides counted slides,
 * blogs printed a date and a read time, summaries listed their specialties. So
 * there is one card, and the difference is a string.
 */
function metaLine(item: MediaItem, kind: MediaKind | null): string {
  const published = formatPublished(item.published_at);

  if (kind === "slide_deck") {
    const count = deckSlides(item).length;
    if (count > 0) return `${count} slides`;
    return deckVideoUrl(item) ? "Video presentation" : published;
  }

  if (kind === "blog") {
    const body = bodyMarkdown(item);
    const minutes = body ? `${readMinutes(body)} min read` : null;
    return [published, minutes].filter(Boolean).join(" · ");
  }

  if (kind === "podcast") {
    return ["7–10 min", "with Ben & Michelle"].join(" · ");
  }

  const specialties = specialtiesOf(item);
  return specialties.length > 0 ? specialties.join(" · ") : published;
}

function previewOf(item: MediaItem): string | null {
  if (item.summary?.trim()) return item.summary;
  const body = bodyMarkdown(item);
  return body ? excerpt(body) : null;
}

export function MediaCardGrid({ children }: { children: ReactNode }) {
  return <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-3">{children}</ul>;
}

/** One card, every kind. `href` comes from `hrefFor` so it works on any arm. */
export function MediaCard({ item, href }: { item: MediaItem; href: string }) {
  const kind = mediaKindOf(item);
  const Icon = kind ? MEDIA_KIND_ICON[kind] : LuFileText;
  const meta = metaLine(item, kind);
  const preview = previewOf(item);

  return (
    <li className="flex">
      <Link
        href={href}
        className={cn(
          t.b2cCardPlain,
          "group flex w-full flex-col px-5 py-[18px] transition-colors hover:border-osce-accent",
        )}
      >
        <div className="flex items-center justify-between gap-2">
          <span className={cn(t.b2cEyebrow, "inline-flex items-center gap-1.5")}>
            <Icon className="h-4 w-4 shrink-0 text-osce-accent" aria-hidden />
            {kind ? MEDIA_KIND_LABELS[kind].one : item.kind}
          </span>
          {item.exam_code ? <Badge tone="accent">{item.exam_code.toUpperCase()}</Badge> : null}
        </div>

        <h3
          className={cn(
            "mt-3 line-clamp-2 text-osce-title font-semibold text-osce-ink-900 transition-colors group-hover:text-osce-accent",
          )}
        >
          {item.title}
        </h3>

        {preview ? <p className={cn("mt-2 line-clamp-3", t.b2cBodyTextMuted)}>{preview}</p> : null}

        <div className="mt-auto flex items-center justify-between gap-3 pt-3.5">
          {meta ? <span className={t.b2cPanelCardMeta}>{meta}</span> : <span />}
          <HiOutlineArrowRight
            className="h-3.5 w-3.5 shrink-0 text-b2c-text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-osce-accent"
            aria-hidden
          />
        </div>
      </Link>
    </li>
  );
}
