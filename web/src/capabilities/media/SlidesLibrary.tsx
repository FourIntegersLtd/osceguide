"use client";

import { Suspense, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";
import { HiOutlinePhoto } from "react-icons/hi2";
import { B2CEmptyState } from "@/foundation/ui";
import { useSurface } from "@/capabilities/SurfaceContext";
import type { MediaItem } from "@/capabilities/media/api";
import { useCurrentExam } from "@/foundation/session";
import { SlidesWorkspace } from "@/capabilities/media/SlidesWorkspace";
import { slidesDeckPath } from "@/capabilities/media/studyPaths";

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
  specialty: string;
  onSpecialtyChange: (specialty: string) => void;
  specialtyOptions: string[];
  hasUncategorized: boolean;
  total: number | null;
  footer?: ReactNode;
};

export function SlidesLibrary({
  items,
  allItemsCount,
  ...specialtyFilter
}: {
  items: MediaItem[];
  allItemsCount: number;
} & SpecialtyFilterProps) {
  return (
    <Suspense fallback={null}>
      <SlidesLibraryInner items={items} allItemsCount={allItemsCount} {...specialtyFilter} />
    </Suspense>
  );
}

function SlidesLibraryInner({
  items,
  allItemsCount,
  ...specialtyFilter
}: {
  items: MediaItem[];
  allItemsCount: number;
} & SpecialtyFilterProps) {
  const { hrefFor } = useSurface();
  const { code: examCode } = useCurrentExam();
  const searchParams = useSearchParams();
  const deckParam = searchParams.get("deck");

  const selected = resolveSelected(items, deckParam);
  const deckHref = (slug: string) => hrefFor(slidesDeckPath(slug));

  if (items.length === 0) {
    return (
      <B2CEmptyState
        icon={HiOutlinePhoto}
        title="No slides available"
        description={
          allItemsCount > 0 && examCode
            ? `Nothing published for ${examCode.toUpperCase()} yet. Switch exam in the menu or upgrade for full access.`
            : "Check back later for new content."
        }
      />
    );
  }

  if (!selected) return null;

  return (
    <SlidesWorkspace
      selected={selected}
      decks={items}
      deckHref={deckHref}
      hrefFor={hrefFor}
      {...specialtyFilter}
    />
  );
}
