"use client";

import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { readMedia, type MediaItem } from "@/capabilities/media/api";
import { DeckView } from "@/capabilities/media/DeckView";
import { SummaryView } from "@/capabilities/media/SummaryView";
import { ArticleView } from "@/capabilities/media/ArticleView";
import { EpisodeView } from "@/capabilities/media/EpisodeView";

/**
 * One item, read the way its kind is meant to be read.
 *
 * The dispatch is the whole of "four folders became one capability": the list,
 * the URL, the loading and the failure are shared, and what differs is the
 * reader — a deck is a presentation beside its siblings, a summary is a
 * clinical brief in tabs, an article is an article, an episode is a player
 * with the rest of the series under it.
 */
export function MediaItemView({ slug }: { slug: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => readMedia(slug, signal), [slug]);

  return (
    <div className="w-full text-left">
      <AsyncBoundary state={state}>{(item) => <Reader item={item} hrefFor={hrefFor} />}</AsyncBoundary>
    </div>
  );
}

function Reader({ item, hrefFor }: { item: MediaItem; hrefFor: (path: string) => string }) {
  if (item.kind === "slide_deck") return <DeckView item={item} hrefFor={hrefFor} />;
  if (item.kind === "summary") return <SummaryView item={item} hrefFor={hrefFor} />;
  if (item.kind === "podcast") return <EpisodeView item={item} hrefFor={hrefFor} />;
  return <ArticleView item={item} hrefFor={hrefFor} />;
}
