"use client";

import { useState } from "react";
import { HiOutlineMagnifyingGlass, HiOutlineXMark } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CEmptyState,
  B2CPageHeader,
  B2CSegmentedTabs,
  Pagination,
  cn,
  productTokens as t,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import {
  MEDIA_KINDS,
  MEDIA_KIND_LABELS,
  filterMediaByExam,
  listAllMedia,
  type MediaItem,
  type MediaKind,
} from "@/capabilities/media/api";
import { useCurrentExam } from "@/foundation/session";
import { MEDIA_KIND_ICON, MediaCard, MediaCardGrid } from "@/capabilities/media/MediaCard";
import { SummaryIndex } from "@/capabilities/media/SummaryIndex";
import { MediaSearchResults } from "@/capabilities/media/MediaSearchResults";

type Filter = MediaKind | "all";

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
    description: "New articles are published regularly — check back soon.",
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
  const state = useAsync((signal) => listAllMedia(kind, signal), [kind]);

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
          className="w-full appearance-none rounded-lg border border-b2c-border bg-b2c-surface-muted py-2.5 pl-10 pr-24 text-left text-osce-body text-osce-ink-900 outline-none placeholder:text-osce-ink-400 focus:border-osce-accent focus:bg-osce-surface focus:outline-none focus:ring-2 focus:ring-osce-accent-subtle [&::-webkit-search-cancel-button]:hidden [&::-webkit-search-decoration]:hidden"
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
              const scoped = filterMediaByExam(items, examCode);
              return scoped.length === 0 ? (
                <B2CEmptyState
                  icon={filter === "all" ? undefined : MEDIA_KIND_ICON[filter]}
                  title={EMPTY[filter].title}
                  description={
                    items.length > 0 && examCode
                      ? `Nothing published for ${examCode.toUpperCase()} yet. Switch exam in the menu or upgrade for full access.`
                      : EMPTY[filter].description
                  }
                />
              ) : filter === "summary" ? (
                <SummaryIndex items={scoped} hrefFor={hrefFor} />
              ) : (
                <PagedGrid items={scoped} hrefFor={hrefFor} />
              );
            }}
          </AsyncBoundary>
        </>
      )}
    </div>
  );
}

/**
 * Paged in the browser, because the whole set is already here.
 *
 * `GET /api/v1/media` pages on an opaque cursor, so there is no total to count
 * pages against until every page has been walked — which the index and the
 * deck sidebar need anyway.
 */
function PagedGrid({ items, hrefFor }: { items: MediaItem[]; hrefFor: (path: string) => string }) {
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(10);

  const start = (page - 1) * perPage;
  const visible = items.slice(start, start + perPage);

  return (
    <div className={cn("space-y-8", items.length <= perPage && "pb-4")}>
      <MediaCardGrid>
        {visible.map((item) => (
          <MediaCard key={item.id} item={item} href={hrefFor(`/library/${item.slug}`)} />
        ))}
      </MediaCardGrid>

      {items.length > perPage ? (
        <Pagination
          currentPage={page}
          totalItems={items.length}
          itemsPerPage={perPage}
          knownTotal
          onPageChange={setPage}
          onItemsPerPageChange={(next) => {
            setPerPage(next);
            setPage(1);
          }}
        />
      ) : null}
    </div>
  );
}
