"use client";

import { Suspense, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { HiOutlinePhoto } from "react-icons/hi2";
import { AsyncBoundary, B2CEmptyState } from "@/foundation/ui";
import type { AsyncState } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import type { MediaItem } from "@/capabilities/media/api";
import { useCurrentExam } from "@/foundation/session";
import { SlidesWorkspace } from "@/capabilities/media/SlidesWorkspace";
import { slidesDeckPath } from "@/capabilities/media/studyPaths";
import type { StudySearch } from "@/capabilities/media/useStudySearch";
import { emptyLibraryDescription, NO_SLIDES_COPY } from "@/capabilities/media/support/emptyCopy";

function resolveSelected(decks: MediaItem[], deckParam: string | null): MediaItem | null {
  if (decks.length === 0) return null;
  if (deckParam) {
    const match = decks.find((deck) => deck.slug === deckParam);
    if (match) return match;
  }
  return decks[0] ?? null;
}

/**
 * Slides tab — B2C two-pane layout with selection in `?deck=`.
 */
type SpecialtyFilterProps = {
  /** The page's one study search. */
  search: StudySearch;
  specialty: string;
  onSpecialtyChange: (specialty: string) => void;
  specialtyOptions: string[];
  hasUncategorized: boolean;
  total: number | null;
  footer?: ReactNode;
};

export function SlidesLibrary({
  state,
  ...specialtyFilter
}: {
  /** The decks read so far. The list stays on screen while it reloads, so a search box keeps focus. */
  state: AsyncState<MediaItem[]>;
} & SpecialtyFilterProps) {
  return (
    <Suspense fallback={null}>
      <SlidesLibraryInner state={state} {...specialtyFilter} />
    </Suspense>
  );
}

function SlidesLibraryInner({
  state,
  ...specialtyFilter
}: {
  state: AsyncState<MediaItem[]>;
} & SpecialtyFilterProps) {
  const { hrefFor } = useSurface();
  const { code: examCode } = useCurrentExam();
  const searchParams = useSearchParams();
  const deckParam = searchParams.get("deck");

  const items = state.data ?? [];
  const selected = resolveSelected(items, deckParam);
  const deckHref = (slug: string) => hrefFor(slidesDeckPath(slug));

  if (state.error) return <AsyncBoundary state={state}>{() => null}</AsyncBoundary>;

  const searching = specialtyFilter.search.urlQuery !== "" || specialtyFilter.specialty !== "all";
  if (items.length === 0 && !state.loading && !searching) {
    return (
      <B2CEmptyState
        icon={HiOutlinePhoto}
        title="No slides available"
        description={emptyLibraryDescription(examCode, NO_SLIDES_COPY)}
      />
    );
  }

  return (
    <SlidesWorkspace
      selected={selected}
      decks={items}
      loading={state.loading}
      deckHref={deckHref}
      hrefFor={hrefFor}
      {...specialtyFilter}
    />
  );
}
