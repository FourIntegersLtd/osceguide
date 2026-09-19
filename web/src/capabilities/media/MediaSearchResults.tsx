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
import { MEDIA_KIND_LABELS, searchMedia } from "@/capabilities/media/api";
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
  hrefFor,
  onClear,
}: {
  query: string;
  hrefFor: (path: string) => string;
  onClear: () => void;
}) {
  const state = useAsync((signal) => searchMedia(query, signal), [query]);

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
        {(page) =>
          page.items.length === 0 ? (
            <B2CEmptyState
              icon={HiOutlineMagnifyingGlass}
              title={`No results for ${query}`}
              description="Try a different search term, or clear the search to see everything."
            />
          ) : (
            <B2CPanelCard className="mt-0">
              <B2CPanelCardHeader>
                <span>Search results</span>
                <span className={t.b2cPanelCardMeta}>{page.items.length} found</span>
              </B2CPanelCardHeader>
              <ul>
                {page.items.map((hit) => {
                  const kind = mediaKindOf(hit);
                  const Icon = kind ? MEDIA_KIND_ICON[kind] : HiOutlineMagnifyingGlass;
                  return (
                    <li key={hit.id}>
                      <Link href={hrefFor(`/library/${hit.slug}`)} className={t.b2cPanelListRow}>
                        <span className="flex min-w-0 items-center gap-3">
                          <Icon className="h-4 w-4 shrink-0 text-osce-accent" aria-hidden />
                          <span className="min-w-0">
                            <span className={cn("block truncate", t.b2cPanelListRowTitle)}>
                              {hit.title}
                            </span>
                            <span className={cn("mt-0.5 block", t.b2cPanelCardMeta)}>
                              {kind ? MEDIA_KIND_LABELS[kind].one : hit.kind}
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
          )
        }
      </AsyncBoundary>
    </div>
  );
}
