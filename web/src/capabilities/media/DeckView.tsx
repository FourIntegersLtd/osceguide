"use client";

import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import { filterMediaByExam, listAllMedia, type MediaItem } from "@/capabilities/media/api";
import { SlidesWorkspace } from "@/capabilities/media/SlidesWorkspace";
import { slidesDeckPath } from "@/capabilities/media/studyPaths";

/**
 * Legacy `/library/[slug]` reader for slide decks — same workspace as the tab.
 */
export function DeckView({ item, hrefFor }: { item: MediaItem; hrefFor: (path: string) => string }) {
  const { code: examCode } = useCurrentExam();
  const decks = useAsync((signal) => listAllMedia("slide_deck", signal), []);
  const deckHref = (slug: string) => hrefFor(slidesDeckPath(slug));

  return (
    <AsyncBoundary state={decks}>
      {(items) => (
        <SlidesWorkspace
          selected={item}
          decks={filterMediaByExam(items, examCode)}
          deckHref={deckHref}
          hrefFor={hrefFor}
          showPageHeader
          showBackLink
        />
      )}
    </AsyncBoundary>
  );
}
