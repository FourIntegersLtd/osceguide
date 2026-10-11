import type { MediaKind } from "@/capabilities/media/api";

/** Side-nav path for each study material kind (B2C-style, not one combined library). */
export const STUDY_KIND_PATH: Record<MediaKind, string> = {
  summary: "/summary",
  slide_deck: "/slides",
  podcast: "/podcast",
  // Public, outside any workspace: articles are the /blogs pages.
  blog: "/blogs",
};

export const STUDY_KIND_LABEL: Record<MediaKind, string> = {
  summary: "A to Z",
  slide_deck: "Slides",
  podcast: "Podcast",
  blog: "Blogs",
};

export function studyListPath(kind: MediaKind): string {
  return STUDY_KIND_PATH[kind];
}

export function slidesDeckPath(slug: string): string {
  return `${STUDY_KIND_PATH.slide_deck}?deck=${encodeURIComponent(slug)}`;
}

export function podcastEpisodePath(slug: string): string {
  return `${STUDY_KIND_PATH.podcast}?episode=${encodeURIComponent(slug)}`;
}

/** In-tab search (drops playback selection params such as `episode`). */
export function studySearchPath(kind: MediaKind, query: string): string {
  return `${STUDY_KIND_PATH[kind]}?q=${encodeURIComponent(query.trim())}`;
}

/** The page for one item: its kind's own route, so the breadcrumb finds its nav item. */
export function studyTabPathForSlug(kind: MediaKind, slug: string): string {
  if (kind === "slide_deck") return slidesDeckPath(slug);
  if (kind === "podcast") return podcastEpisodePath(slug);
  return `${STUDY_KIND_PATH[kind]}/${slug}`;
}

/**
 * The address a link to one item opens. Articles are public `/blogs` pages and
 * live outside the workspace, so they skip `hrefFor`; every other kind opens in
 * the workspace.
 */
export function studyItemHref(hrefFor: (path: string) => string, kind: MediaKind, slug: string): string {
  return kind === "blog" ? studyTabPathForSlug(kind, slug) : hrefFor(studyTabPathForSlug(kind, slug));
}
