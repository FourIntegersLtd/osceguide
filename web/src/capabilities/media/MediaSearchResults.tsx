"use client";

import Link from "next/link";
import { HiOutlineArrowRight, HiOutlineMagnifyingGlass } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CEmptyState,
  B2CPanelCard,
  B2CPanelCardHeader,
  Button,
  cn,
  productTokens as t,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import {
  MEDIA_KIND_LABELS,
  searchMediaWithFallback,
  type MediaKind,
} from "@/capabilities/media/api";
import { studyItemHref } from "@/capabilities/media/studyPaths";
import { MEDIA_KIND_ICON, mediaKindOf } from "@/capabilities/media/MediaCard";

/**
 * One search box over the whole library.
 *
 * The retiring client searched two lists separately, each with its own box and
 * its own idea of a match — the A-to-Z filtered summary names server-side, the
 * blog list filtered post titles. `GET /api/v1/media-search` is a vector search
 * across every kind, so a reader who does not know whether the answer is in a
 * summary or a deck finds it either way. The result rows say which they are.
 */
export function MediaSearchResults({
  query,
  examCode,
  hrefFor,
  onClear,
  kind = null,
}: {
  query: string;
  examCode?: string | null;
  hrefFor: (path: string) => string;
  onClear: () => void;
  kind?: MediaKind | null;
}) {
  const state = useAsync(
    (signal) => searchMediaWithFallback(query, { examCode, kind }, signal),
    [query, examCode, kind],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className={t.b2cBodyTextMuted}>
          Results for <span className="font-medium text-osce-ink-900">{query}</span>
        </p>
        <Button variant="secondary" size="sm" onClick={onClear}>
          Clear search
        </Button>
      </div>

      <AsyncBoundary state={state}>
        {(page) => {
          const items = page.items;
          return items.length === 0 ? (
            <B2CEmptyState
              icon={HiOutlineMagnifyingGlass}
              title={`No results for ${query}`}
              description="Try a different search term, or clear the search to see everything."
            />
          ) : (
            <B2CPanelCard className="mt-0">
              <B2CPanelCardHeader>
                <span>Search results</span>
                <span className={t.b2cPanelCardMeta}>{items.length} found</span>
              </B2CPanelCardHeader>
              <ul>
                {items.map((hit) => {
                  const hitKind = mediaKindOf(hit);
                  const Icon = hitKind ? MEDIA_KIND_ICON[hitKind] : HiOutlineMagnifyingGlass;
                  const href = hitKind
                    ? studyItemHref(hrefFor, hitKind, hit.slug)
                    : hrefFor(`/library/${hit.slug}`);
                  return (
                    <li key={hit.id}>
                      <Link href={href} className={t.b2cPanelListRow}>
                        <span className="flex min-w-0 items-center gap-3">
                          <Icon className="h-4 w-4 shrink-0 text-osce-accent" aria-hidden />
                          <span className="min-w-0">
                            <span className={cn("block truncate", t.b2cPanelListRowTitle)}>
                              {hit.title}
                            </span>
                            <span className={cn("mt-0.5 block", t.b2cPanelCardMeta)}>
                              {hitKind ? MEDIA_KIND_LABELS[hitKind].one : hit.kind}
                            </span>
                          </span>
                        </span>
                        <HiOutlineArrowRight
                          className="h-3.5 w-3.5 shrink-0 text-b2c-text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-osce-accent"
                          aria-hidden
                        />
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </B2CPanelCard>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}
