"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { HiOutlineMagnifyingGlass, HiOutlineXMark } from "react-icons/hi2";
import {
  Alert,
  AsyncBoundary,
  B2CEmptyState,
  B2CPageHeader,
  Button,
  cn,
  productTokens as t,
  iconSearchInputClassName,
} from "@/foundation/ui";
import { useCursorPages, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { listMedia, listAllMedia, specialtiesOf, type MediaKind } from "@/capabilities/media/api";
import { useCurrentExam } from "@/foundation/session";
import { MEDIA_KIND_ICON } from "@/capabilities/media/MediaCard";
import { ArticlesLibrary } from "@/capabilities/media/ArticlesLibrary";
import { PodcastLibrary } from "@/capabilities/media/PodcastLibrary";
import { SlidesLibrary } from "@/capabilities/media/SlidesLibrary";
import { SummaryIndex } from "@/capabilities/media/SummaryIndex";
import { MediaSearchResults } from "@/capabilities/media/MediaSearchResults";
import { studyListPath, studySearchPath } from "@/capabilities/media/studyPaths";

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
  const router = useRouter();
  const { code: examCode } = useCurrentExam();
  const searchParams = useSearchParams();
  const urlQuery = searchParams.get("q")?.trim() ?? "";
  const [term, setTerm] = useState(urlQuery);

  // Slide decks alone offer a specialty filter, applied in SQL rather than
  // over an already-loaded page.
  const [specialty, setSpecialty] = useState("all");
  const specialtyFilter =
    specialty === "all" ? {} : specialty === "other" ? { hasSpecialty: false } : { specialty };

  // A page at a time, scoped by exam in SQL. This used to walk every cursor
  // up front and then filter the whole catalogue by exam in the browser.
  const pages = useCursorPages(
    (cursor, signal) =>
      listMedia(
        {
          kind,
          cursor,
          limit: MEDIA_KIND_PAGE_LIMIT,
          examCode,
          // Articles read newest-published-first; the server default is
          // creation order, which drifted from publish order once drafts
          // could sit unpublished for a while before going live.
          sort: kind === "blog" ? "published" : undefined,
          ...specialtyFilter,
        },
        signal,
      ),
    [kind, examCode, specialty],
  );
  const state = pages.state;

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

  useEffect(() => {
    setTerm(urlQuery);
  }, [urlQuery]);

  const clearSearch = () => {
    setTerm("");
    router.replace(hrefFor(studyListPath(kind)), { scroll: false });
  };

  return (
    <div className="w-full text-left">
      <B2CPageHeader title={copy.title} subtitle={copy.subtitle} />

      {searchEnabled ? (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            const next = term.trim();
            if (next === "") return;
            router.replace(hrefFor(studySearchPath(kind, next)), { scroll: false });
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
      ) : null}

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
                {items.length === 0 ? (
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
                  />
                ) : kind === "podcast" ? (
                  <PodcastLibrary items={items} allItemsCount={items.length} />
                ) : (
                  <ArticlesLibrary items={items} hrefFor={hrefFor} />
                )}

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
          </AsyncBoundary>
        </div>
      )}
    </div>
  );
}
