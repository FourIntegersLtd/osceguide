"use client";

import { Suspense, useState } from "react";
import { HiOutlineMagnifyingGlass, HiOutlineXMark } from "react-icons/hi2";
import {
  Alert,
  AsyncBoundary,
  B2CEmptyState,
  B2CPageHeader,
  Button,
  cn,
  iconSearchInputClassName,
} from "@/foundation/ui";
import { useCursorPages, useAsync, type AsyncState, type CursorPages } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { listMedia, listAllMedia, specialtiesOf, type MediaItem, type MediaKind } from "@/capabilities/media/api";
import { useCurrentExam } from "@/foundation/session";
import { MEDIA_KIND_ICON } from "@/capabilities/media/MediaCard";
import { ArticlesLibrary } from "@/capabilities/media/ArticlesLibrary";
import { PodcastLibrary } from "@/capabilities/media/PodcastLibrary";
import { SlidesLibrary } from "@/capabilities/media/SlidesLibrary";
import { SummaryIndex } from "@/capabilities/media/SummaryIndex";
import { MediaSearchResults } from "@/capabilities/media/MediaSearchResults";
import { CLIENT_PAGE_SIZE, sortByTitle } from "@/capabilities/media/catalogue";
import { useStudySearch } from "@/capabilities/media/useStudySearch";

const PAGE_COPY: Record<
  MediaKind,
  { title: string; subtitle: string; emptyTitle: string; emptyDescription: string }
> = {
  summary: {
    title: "A to Z",
    subtitle: "Clinical summaries to revise between stations.",
    emptyTitle: "No summaries yet",
    emptyDescription: "Summaries appear here as they are published for your exam.",
  },
  slide_deck: {
    title: "Slides",
    subtitle: "Video presentations by topic.",
    emptyTitle: "No slides available",
    emptyDescription: "Check back later for new content.",
  },
  podcast: {
    title: "Podcast",
    subtitle: "Listen to episodes between stations.",
    emptyTitle: "No episodes yet",
    emptyDescription: "Episodes appear here as they are published.",
  },
  blog: {
    title: "Articles",
    subtitle: "Articles and updates from the study team.",
    emptyTitle: "No articles found",
    emptyDescription: "New articles are published regularly, so check back soon.",
  },
};

/**
 * One study-material kind per route — the B2C layout without a combined filter.
 */
export function MediaKindLibrary({ kind }: { kind: MediaKind }) {
  return (
    <Suspense fallback={null}>
      <MediaKindLibraryBody kind={kind} />
    </Suspense>
  );
}

/** The backend's page cap on `GET /api/v1/media` is 100; a screen doesn't need that much at once. */
const MEDIA_KIND_PAGE_LIMIT = 24;

function MediaKindLibraryBody({ kind }: { kind: MediaKind }) {
  const copy = PAGE_COPY[kind];
  const { hrefFor } = useSurface();
  const { code: examCode } = useCurrentExam();
  const { term, setTerm, urlQuery, clear: clearSearch } = useStudySearch(kind);

  // Slide decks alone offer a specialty filter, applied in SQL rather than
  // over an already-loaded page.
  const [specialty, setSpecialty] = useState("all");
  // Slides search inside their own list, matched on title and summary in SQL.
  const deckQuery = kind === "slide_deck" ? urlQuery : "";
  const specialtyFilter =
    specialty === "all" ? {} : specialty === "other" ? { hasSpecialty: false } : { specialty };

  // A to Z and Podcasts read the whole catalogue once, sort it by title and show it ten at
  // a time: a later server page would sort in above the rows already on screen.
  const clientPaged = kind === "summary" || kind === "podcast";
  const catalogue = useAsync(
    (signal) =>
      clientPaged ? listAllMedia(kind, signal, examCode).then(sortByTitle) : Promise.resolve([]),
    [kind, examCode, clientPaged],
  );
  const [shown, setShown] = useState(CLIENT_PAGE_SIZE);
  const everything = catalogue.data ?? [];

  // Slides and Articles: a server page at a time, scoped by exam in SQL.
  const cursorPages = useCursorPages(
    (cursor, signal) =>
      clientPaged
        ? Promise.resolve({ items: [] })
        : listMedia(
        {
          kind,
          cursor,
          limit: MEDIA_KIND_PAGE_LIMIT,
          examCode,
          // Articles read newest-published-first; the server default is
          // creation order, which drifted from publish order once drafts
          // could sit unpublished for a while before going live.
          sort: kind === "blog" ? "published" : undefined,
          q: deckQuery || undefined,
          ...specialtyFilter,
        },
        signal,
      ),
    [kind, examCode, specialty, deckQuery, clientPaged],
  );
  const state: AsyncState<MediaItem[]> = clientPaged
    ? { ...catalogue, data: catalogue.data === null ? null : everything.slice(0, shown) }
    : cursorPages.state;
  const pages: MoreRows = clientPaged
    ? {
        hasMore: shown < everything.length,
        loadingMore: false,
        moreError: null,
        loadMore: () => setShown((count) => count + CLIENT_PAGE_SIZE),
      }
    : cursorPages;

  // The specialty picker's own option list, from a wider unfiltered fetch —
  // an already-filtered page can't tell you what else was on offer.
  const specialtyOptions = useAsync(
    (signal) => (kind === "slide_deck" ? listAllMedia(kind, signal, examCode) : Promise.resolve([])),
    [kind, examCode],
  );
  const deckSpecialties = [...new Set((specialtyOptions.data ?? []).flatMap(specialtiesOf))].sort();
  const deckHasUncategorized = (specialtyOptions.data ?? []).some(
    (deck) => specialtiesOf(deck).length === 0,
  );
  const searchEnabled = kind !== "slide_deck";
  const showSearchResults = searchEnabled && urlQuery.length > 0;
  const searchForm = (
    <form
      onSubmit={(event) => event.preventDefault()}
      className="mb-6"
      role="search"
    >
      <div className="relative w-full">
        <HiOutlineMagnifyingGlass
          className="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-osce-ink-400"
          aria-hidden
        />
        <input
          type="search"
          placeholder="Search for a topic or condition"
          value={term}
          onChange={(event) => setTerm(event.target.value)}
          aria-label="Search study material"
          className={cn(iconSearchInputClassName, "pr-10 text-left")}
        />
        {term ? (
          <button
            type="button"
            onClick={clearSearch}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-osce-ink-400 transition-colors hover:bg-osce-border-light hover:text-osce-ink-600"
            aria-label="Clear search"
          >
            <HiOutlineXMark className="h-3.5 w-3.5" aria-hidden />
          </button>
        ) : null}
      </div>
    </form>
  );

  return (
    <div className="w-full text-left">
      <B2CPageHeader title={copy.title} subtitle={copy.subtitle} />

      {searchEnabled ? searchForm : null}

      {showSearchResults ? (
        <MediaSearchResults
          query={urlQuery}
          examCode={examCode}
          hrefFor={hrefFor}
          onClear={clearSearch}
          kind={kind}
        />
      ) : (
        <div className={cn(!searchEnabled && "mt-6")}>
          <AsyncBoundary state={state}>
            {(items) => (
              <>
                {items.length === 0 && deckQuery === "" ? (
                  <B2CEmptyState
                    icon={MEDIA_KIND_ICON[kind]}
                    title={copy.emptyTitle}
                    description={
                      examCode
                        ? `Nothing published for ${examCode.toUpperCase()} yet. Switch exam in the menu or upgrade for full access.`
                        : copy.emptyDescription
                    }
                  />
                ) : kind === "summary" ? (
                  <SummaryIndex items={items} hrefFor={hrefFor} />
                ) : kind === "slide_deck" ? (
                  <SlidesLibrary
                    items={items}
                    allItemsCount={items.length}
                    specialty={specialty}
                    onSpecialtyChange={setSpecialty}
                    specialtyOptions={deckSpecialties}
                    hasUncategorized={deckHasUncategorized}
                    total={cursorPages.total}
                    footer={<LoadMore pages={pages} className="flex justify-center p-3" />}
                  />
                ) : kind === "podcast" ? (
                  <PodcastLibrary items={items} catalogue={everything} allItemsCount={everything.length} />
                ) : (
                  <ArticlesLibrary items={items} hrefFor={hrefFor} />
                )}

                {/* Slides draw it inside their own list. */}
                {kind === "slide_deck" ? null : <LoadMore pages={pages} className="mt-6 flex justify-center" />}
              </>
            )}
          </AsyncBoundary>
        </div>
      )}
    </div>
  );
}

type MoreRows = Pick<CursorPages<unknown>, "hasMore" | "loadingMore" | "moreError" | "loadMore">;

function LoadMore({ pages, className }: { pages: MoreRows; className: string }) {
  return (
    <>
      {pages.moreError ? (
        <Alert tone="danger">Could not load more: {pages.moreError.message}</Alert>
      ) : null}
      {pages.hasMore ? (
        <div className={className}>
          <Button variant="secondary" size="sm" disabled={pages.loadingMore} onClick={pages.loadMore}>
            {pages.loadingMore ? "Loading…" : "Load more"}
          </Button>
        </div>
      ) : null}
    </>
  );
}
