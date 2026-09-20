import type { MediaKind } from "@/capabilities/media/api";

/** Side-nav path for each study material kind (B2C-style, not one combined library). */
export const STUDY_KIND_PATH: Record<MediaKind, string> = {
  summary: "/summary",
  slide_deck: "/slides",
  podcast: "/podcast",
  blog: "/articles",
};

export const STUDY_KIND_LABEL: Record<MediaKind, string> = {
  summary: "A to Z",
  slide_deck: "Slides",
  podcast: "Podcast",
  blog: "Articles",
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

/** Tab URL for an unlocked library item (summaries and articles stay on `/library`). */
export function studyTabPathForSlug(kind: MediaKind, slug: string): string {
  if (kind === "slide_deck") return slidesDeckPath(slug);
  if (kind === "podcast") return podcastEpisodePath(slug);
  return `/library/${slug}`;
}
