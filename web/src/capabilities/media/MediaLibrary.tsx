"use client";

import { studyTabPathForSlug } from "@/capabilities/media/studyPaths";
import { useState } from "react";
import { HiOutlineMagnifyingGlass, HiOutlineXMark } from "react-icons/hi2";
import {
  Alert,
  AsyncBoundary,
  B2CEmptyState,
  B2CPageHeader,
  B2CSegmentedTabs,
  Button,
  productTokens as t,
  iconSearchInputClassName,
  cn,
} from "@/foundation/ui";
import { useCursorPages } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import {
  MEDIA_KINDS,
  MEDIA_KIND_LABELS,
  listMedia,
  type MediaItem,
  type MediaKind,
} from "@/capabilities/media/api";
import { useCurrentExam } from "@/foundation/session";
import { MEDIA_KIND_ICON, MediaCard, MediaCardGrid, mediaKindOf } from "@/capabilities/media/MediaCard";
import { SummaryIndex } from "@/capabilities/media/SummaryIndex";
import { MediaSearchResults } from "@/capabilities/media/MediaSearchResults";

type Filter = MediaKind | "all";

/** The backend's page cap on `GET /api/v1/media` is 100; a screen doesn't need that much at once. */
const MEDIA_LIBRARY_PAGE_LIMIT = 24;

const EMPTY: Record<Filter, { title: string; description: string }> = {
  all: {
    title: "Nothing published yet",
    description: "Study material appears here as it is published for your exams.",
  },
  slide_deck: {
    title: "No slides available",
    description: "Check back later for new content.",
  },
  summary: {
    title: "No summaries yet",
    description: "Summaries appear here as they are published.",
  },
  blog: {
    title: "No articles found",
    description: "New articles are published regularly, so check back soon.",
  },
  podcast: {
    title: "No episodes yet",
    description: "Episodes appear here as they are published.",
  },
};

/**
 * The study library.
 *
 * Two nav items in the retiring client — "Slides" and "A to Z" — plus a blog
 * and a podcast that hung off a summary. On this backend all four are one
 * `media` row with a `kind`, so they are one screen with a filter, and each
 * kind keeps the way it is meant to be read: an index of letters for the
 * A-to-Z, a deck viewer for a presentation, an article for a post.
 *
 * Mounted on Train and Assess from this one file. It asks the surface only for
 * its base path, so an institution's trainees get the decks and summaries
 * their programme publishes without a line of institution-specific code here.
 */
export function MediaLibrary({ initialKind = null }: { initialKind?: MediaKind | null }) {
  const { hrefFor } = useSurface();
  const { code: examCode } = useCurrentExam();
  const [filter, setFilter] = useState<Filter>(initialKind ?? "all");
  const [term, setTerm] = useState("");
  const [query, setQuery] = useState("");

  const kind = filter === "all" ? null : filter;
  // A page at a time, scoped by exam in SQL. This used to walk every cursor
  // up front and then filter the whole catalogue by exam in the browser.
  const pages = useCursorPages(
    (cursor, signal) => listMedia({ kind, cursor, limit: MEDIA_LIBRARY_PAGE_LIMIT, examCode }, signal),
    [kind, examCode],
  );
  const state = pages.state;

  const clearSearch = () => {
    setTerm("");
    setQuery("");
  };

  return (
    <div className="w-full text-left">
      <B2CPageHeader
        title="Study material"
        subtitle="Slide decks, summaries, articles and podcast episodes."
      />

      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (term.trim() !== "") setQuery(term.trim());
        }}
        className="mb-8 mt-6 flex justify-end"
        role="search"
      >
        <div className="relative w-full max-w-md">
        <HiOutlineMagnifyingGlass
          className="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-osce-ink-400"
          aria-hidden
        />
        <input
          type="search"
          placeholder="Search for a topic or condition..."
          value={term}
          onChange={(event) => setTerm(event.target.value)}
          aria-label="Search study material"
          className={cn(iconSearchInputClassName, "pr-24 text-left")}
        />
        <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1.5">
          {term ? (
            <button
              type="button"
              onClick={clearSearch}
              className="rounded-md p-1.5 text-osce-ink-400 transition-colors hover:bg-osce-border-light hover:text-osce-ink-600"
              aria-label="Clear search"
            >
              <HiOutlineXMark className="h-3.5 w-3.5" aria-hidden />
            </button>
          ) : null}
          {term.trim() !== "" ? (
            <button type="submit" className={t.b2cButtonPrimarySm}>
              Search
            </button>
          ) : null}
        </div>
        </div>
      </form>

      {query ? (
        <MediaSearchResults
          query={query}
          examCode={examCode}
          hrefFor={hrefFor}
          onClear={clearSearch}
        />
      ) : (
        <>
          <B2CSegmentedTabs
            items={[
              { id: "all", label: "Everything" },
              ...MEDIA_KINDS.map((option) => ({
                id: option,
                label: MEDIA_KIND_LABELS[option].many,
              })),
            ]}
            value={filter}
            onChange={setFilter}
            aria-label="Material type"
          />

          <AsyncBoundary state={state}>
            {(items) => {
              return items.length === 0 ? (
                <B2CEmptyState
                  icon={filter === "all" ? undefined : MEDIA_KIND_ICON[filter]}
                  title={EMPTY[filter].title}
                  description={
                    examCode
                      ? `Nothing published for ${examCode.toUpperCase()} yet. Switch exam in the menu or upgrade for full access.`
                      : EMPTY[filter].description
                  }
                />
              ) : filter === "summary" ? (
                <SummaryIndex items={items} hrefFor={hrefFor} />
              ) : (
                <MediaGrid items={items} hrefFor={hrefFor} />
              );
            }}
          </AsyncBoundary>

          {pages.moreError ? (
            <Alert tone="danger">Could not load more: {pages.moreError.message}</Alert>
          ) : null}
          {pages.hasMore ? (
            <div className="mt-6 flex justify-center">
              <Button
                variant="secondary"
                size="sm"
                disabled={pages.loadingMore}
                onClick={pages.loadMore}
              >
                {pages.loadingMore ? "Loading…" : "Load more"}
              </Button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}

/**
 * The grid for slide decks, blogs and podcast episodes.
 *
 * One page's worth grows into more as `useCursorPages` answers "load more" —
 * the A-to-Z index (`SummaryIndex`) is the only view that still needs the
 * whole set grouped at once, and that grows the same way.
 */
function MediaGrid({ items, hrefFor }: { items: MediaItem[]; hrefFor: (path: string) => string }) {
  return (
    <div className="space-y-8">
      <MediaCardGrid>
        {items.map((item) => (
          <MediaCard key={item.id} item={item} href={hrefFor(studyTabPathForSlug(mediaKindOf(item) ?? "summary", item.slug))} />
        ))}
      </MediaCardGrid>
    </div>
  );
}
