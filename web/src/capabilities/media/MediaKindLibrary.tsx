"use client";

import { Suspense, useState, type ReactNode } from "react";
import { Alert, AsyncBoundary, B2CEmptyState, B2CPageHeader, Button } from "@/foundation/ui";
import { useCursorPages, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { listMedia, listAllMedia, specialtiesOf, type MediaKind } from "@/capabilities/media/api";
import { useCurrentExam } from "@/foundation/session";
import { MEDIA_KIND_ICON } from "@/capabilities/media/MediaCard";
import { ArticlesLibrary } from "@/capabilities/media/ArticlesLibrary";
import { PodcastLibrary } from "@/capabilities/media/PodcastLibrary";
import { SlidesLibrary } from "@/capabilities/media/SlidesLibrary";
import { SummaryIndex, SummaryIndexNav } from "@/capabilities/media/SummaryIndex";
import { MediaSearchResults } from "@/capabilities/media/MediaSearchResults";
import type { SummaryView } from "@/capabilities/media/summaryGroups";
import { B2CHero } from "@/foundation/ui/B2CHero";
import { StudySearchBox } from "@/capabilities/media/StudySearchBox";
import { useClientPagedCatalogue } from "@/capabilities/media/useClientPagedCatalogue";
import { useStudySearch, type StudySearch } from "@/capabilities/media/useStudySearch";

const PAGE_COPY: Record<
  MediaKind,
  { title: string; subtitle?: string; emptyTitle: string; emptyDescription: string }
> = {
  summary: {
    title: "A to Z",
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

/** The page's one study search, read once here and handed down to whatever lists the results. */
function MediaKindLibraryBody({ kind }: { kind: MediaKind }) {
  const search = useStudySearch(kind);
  return kind === "summary" || kind === "podcast" ? (
    <ClientPagedLibrary kind={kind} search={search} />
  ) : (
    <CursorLibrary kind={kind} search={search} />
  );
}

/** What every kind's page shares: the header, a search box over the list, and the search results. */
function LibraryFrame({
  kind,
  search,
  showSearchBox = true,
  sticky = false,
  controls,
  children,
}: {
  kind: MediaKind;
  search: StudySearch;
  /** Slides search inside their own list, so the page draws no box of its own. */
  showSearchBox?: boolean;
  /** A to Z keeps the box and its tabs in place while the list scrolls. */
  sticky?: boolean;
  /** Under the box: A to Z's tabs and jump links. Hidden while search results show. */
  controls?: ReactNode;
  children: ReactNode;
}) {
  const copy = PAGE_COPY[kind];
  const { hrefFor } = useSurface();
  const { code: examCode } = useCurrentExam();
  const showSearchResults = showSearchBox && search.urlQuery.length > 0;
  const box = (
    <StudySearchBox
      term={search.term}
      onTermChange={search.setTerm}
      onClear={search.clear}
      label="Search study material"
      placeholder="Search for a topic or condition"
    />
  );

  return (
    <div className="w-full text-left">
      <B2CPageHeader title={copy.title} subtitle={copy.subtitle} />

      {kind === "summary" && !showSearchResults ? (
        <B2CHero title="Revise common primary care conditions" className="mb-6">
          Each summary has a clinical and a psychological section, which you can talk through with Athena.
        </B2CHero>
      ) : null}

      {sticky ? (
        // Search, tabs and the jump row stay put while the list scrolls.
        <div className="sticky top-0 z-20 -mx-1 bg-osce-surface px-1 pb-4">
          <div className="mb-6">{box}</div>
          {showSearchResults ? null : controls}
        </div>
      ) : showSearchBox ? (
        <div className="mb-6">{box}</div>
      ) : null}

      {showSearchResults ? (
        <MediaSearchResults
          query={search.urlQuery}
          examCode={examCode}
          hrefFor={hrefFor}
          onClear={search.clear}
          kind={kind}
        />
      ) : (
        <div className={showSearchBox ? undefined : "mt-6"}>{children}</div>
      )}
    </div>
  );
}

function EmptyKind({ kind }: { kind: MediaKind }) {
  const copy = PAGE_COPY[kind];
  const { code: examCode } = useCurrentExam();
  return (
    <B2CEmptyState
      icon={MEDIA_KIND_ICON[kind]}
      title={copy.emptyTitle}
      description={
        examCode
          ? `Nothing published for ${examCode.toUpperCase()} yet. Switch exam in the menu or upgrade for full access.`
          : copy.emptyDescription
      }
    />
  );
}

/** A to Z and Podcasts: the whole catalogue read once, shown ten rows at a time. */
function ClientPagedLibrary({ kind, search }: { kind: "summary" | "podcast"; search: StudySearch }) {
  const { hrefFor } = useSurface();
  const { code: examCode } = useCurrentExam();
  const { state, everything, rows } = useClientPagedCatalogue(kind, examCode);
  const [summaryView, setSummaryView] = useState<SummaryView>("az");

  return (
    <LibraryFrame
      kind={kind}
      search={search}
      sticky={kind === "summary"}
      controls={
        kind === "summary" ? (
          // The links come from the whole catalogue, so a letter past the shown rows still has one.
          <SummaryIndexNav
            items={everything}
            view={summaryView}
            onViewChange={setSummaryView}
            onShowAll={rows.showAll}
          />
        ) : null
      }
    >
      <AsyncBoundary state={state}>
        {(items) => (
          <>
            {items.length === 0 ? (
              <EmptyKind kind={kind} />
            ) : kind === "summary" ? (
              <SummaryIndex items={items} view={summaryView} hrefFor={hrefFor} />
            ) : (
              <PodcastLibrary items={items} catalogue={everything} allItemsCount={everything.length} />
            )}
            <LoadMore hasMore={rows.hasMore} onLoadMore={rows.loadMore} className="mt-6 flex justify-center" />
          </>
        )}
      </AsyncBoundary>
    </LibraryFrame>
  );
}

/** Slides and Articles: a server page at a time, scoped by exam in SQL. */
function CursorLibrary({ kind, search }: { kind: "slide_deck" | "blog"; search: StudySearch }) {
  const { hrefFor } = useSurface();
  const { code: examCode } = useCurrentExam();

  // Slide decks alone offer a specialty filter, applied in SQL rather than over an
  // already-loaded page, and search inside their own list, matched on title and summary in SQL.
  const [specialty, setSpecialty] = useState("all");
  const deckQuery = kind === "slide_deck" ? search.urlQuery : "";
  const specialtyFilter =
    specialty === "all" ? {} : specialty === "other" ? { hasSpecialty: false } : { specialty };

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
          q: deckQuery || undefined,
          ...specialtyFilter,
        },
        signal,
      ),
    [kind, examCode, specialty, deckQuery],
  );

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

  if (kind === "slide_deck") {
    return (
      <LibraryFrame kind={kind} search={search} showSearchBox={false}>
        <SlidesLibrary
          state={pages.state}
          search={search}
          specialty={specialty}
          onSpecialtyChange={setSpecialty}
          specialtyOptions={deckSpecialties}
          hasUncategorized={deckHasUncategorized}
          total={pages.total}
          footer={
            <LoadMore
              hasMore={pages.hasMore}
              loading={pages.loadingMore}
              error={pages.moreError}
              onLoadMore={pages.loadMore}
              className="flex justify-center p-3"
            />
          }
        />
      </LibraryFrame>
    );
  }

  return (
    <LibraryFrame kind={kind} search={search}>
      <AsyncBoundary state={pages.state}>
        {(items) => (
          <>
            {items.length === 0 ? <EmptyKind kind={kind} /> : <ArticlesLibrary items={items} hrefFor={hrefFor} />}
            <LoadMore
              hasMore={pages.hasMore}
              loading={pages.loadingMore}
              error={pages.moreError}
              onLoadMore={pages.loadMore}
              className="mt-6 flex justify-center"
            />
          </>
        )}
      </AsyncBoundary>
    </LibraryFrame>
  );
}

function LoadMore({
  hasMore,
  loading = false,
  error = null,
  onLoadMore,
  className,
}: {
  hasMore: boolean;
  loading?: boolean;
  error?: Error | null;
  onLoadMore: () => void;
  className: string;
}) {
  return (
    <>
      {error ? <Alert tone="danger">Could not load more: {error.message}</Alert> : null}
      {hasMore ? (
        <div className={className}>
          <Button variant="secondary" size="sm" disabled={loading} onClick={onLoadMore}>
            {loading ? "Loading…" : "Load more"}
          </Button>
        </div>
      ) : null}
    </>
  );
}
