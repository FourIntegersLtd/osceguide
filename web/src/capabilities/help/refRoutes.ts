import type { CardLink, CardRef } from "@/foundation/livekit/guidance";
import type { MediaKind } from "@/capabilities/media/api";
import { libraryHref, stationHref } from "@/capabilities/stations/routes";
import { STUDY_KIND_LABEL, studyTabPathForSlug } from "@/capabilities/media/studyPaths";

/**
 * Where something Athena put on screen opens.
 *
 * The backend's card ref is `{kind, id, slug}`, and `slug` is always what the
 * page is addressed by: a media item's slug, a help article's slug, and for a
 * station its library id (the `id` is the version that was practised). A help
 * article has no page of its own — help is the dock — so it opens in place
 * through `openHelpArticle`, and without one it has no link.
 */
const MEDIA_EYEBROW: Record<MediaKind, string> = {
  summary: "Summary",
  slide_deck: "Slides",
  podcast: "Podcast",
  blog: "Article",
};

function isMediaKind(kind: string): kind is MediaKind {
  return Object.hasOwn(MEDIA_EYEBROW, kind);
}

export function cardLinkFor(
  ref: CardRef,
  {
    hrefFor,
    openHelpArticle,
  }: { hrefFor: (path: string) => string; openHelpArticle?: (slug: string) => void },
): CardLink | null {
  const slug = ref.slug?.trim();

  if (ref.kind === "station") {
    return slug
      ? { eyebrow: "Station", label: "Open the station", href: stationHref(hrefFor, slug) }
      : { eyebrow: "Station", label: "Open the station library", href: libraryHref(hrefFor) };
  }

  if (ref.kind === "help") {
    if (!slug || !openHelpArticle) return null;
    return { eyebrow: "Help", label: "Read the guide", onOpen: () => openHelpArticle(slug) };
  }

  if (isMediaKind(ref.kind) && slug) {
    return {
      eyebrow: MEDIA_EYEBROW[ref.kind],
      label: `Open in ${STUDY_KIND_LABEL[ref.kind]}`,
      href: hrefFor(studyTabPathForSlug(ref.kind, slug)),
    };
  }

  return null;
}
