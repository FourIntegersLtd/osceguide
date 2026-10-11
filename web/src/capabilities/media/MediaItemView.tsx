"use client";

import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { readMedia, type MediaItem } from "@/capabilities/media/api";
import { SummaryView } from "@/capabilities/media/SummaryView";
import { LockedMediaGate } from "@/capabilities/media/LockedMediaGate";
import { StudyTabRedirect } from "@/capabilities/media/StudyTabRedirect";
import { podcastEpisodePath, slidesDeckPath, studyItemHref } from "@/capabilities/media/studyPaths";
import { useRecordView } from "@/capabilities/account/useRecordView";

/**
 * One item, read the way its kind is meant to be read.
 *
 * The dispatch is the whole of "four folders became one capability": the list,
 * the URL, the loading and the failure are shared, and what differs is the
 * reader — a deck is a presentation beside its siblings, a summary is a
 * clinical brief in tabs, an article is sent to its public page, an episode is a player
 * with the rest of the series under it.
 */
export function MediaItemView({ slug }: { slug: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => readMedia(slug, signal), [slug]);
  // Decks and episodes redirect to their own tab, which records them there.
  const read = state.data;
  useRecordView(
    read && !read.locked && read.kind === "summary"
      ? { kind: "viewed", ref_kind: read.kind, ref_id: read.slug, title: read.title, exam_code: read.exam_code }
      : null,
  );

  return (
    <div className="w-full text-left">
      <AsyncBoundary state={state}>{(item) => <Reader item={item} hrefFor={hrefFor} />}</AsyncBoundary>
    </div>
  );
}

function Reader({ item, hrefFor }: { item: MediaItem; hrefFor: (path: string) => string }) {
  if (item.locked) {
    return (
      <div className="w-full text-left">
        <LockedMediaGate item={item} />
      </div>
    );
  }
  if (item.kind === "slide_deck") {
    return <StudyTabRedirect hrefFor={hrefFor} path={slidesDeckPath(item.slug)} />;
  }
  if (item.kind === "summary") {
    return <SummaryView item={item} hrefFor={hrefFor} />;
  }
  if (item.kind === "podcast") {
    return <StudyTabRedirect hrefFor={hrefFor} path={podcastEpisodePath(item.slug)} />;
  }
  // An article is a public /blogs page, not a workspace screen.
  return <StudyTabRedirect hrefFor={(path) => path} path={studyItemHref(hrefFor, "blog", item.slug)} />;
}
