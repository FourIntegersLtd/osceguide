import { platformRequest, type components } from "@/foundation/platform-client";

export type MediaItem = components["schemas"]["MediaRead"];
export type MediaPage = components["schemas"]["Page_MediaRead_"];

/**
 * The four kinds the `media` slice stores.
 *
 * One table with a `kind`, where the consumer backend had sixteen collections
 * — four kinds across four exams — with the same publish-and-read logic copied
 * into each. That is why this is a list and not four modules.
 */
// The backend's spelling (`media/domain.py`), not a display name.
export const MEDIA_KINDS = ["slide_deck", "summary", "blog", "podcast"] as const;
export type MediaKind = (typeof MEDIA_KINDS)[number];

export const MEDIA_KIND_LABELS: Record<MediaKind, { one: string; many: string }> = {
  slide_deck: { one: "Slide deck", many: "Slide decks" },
  summary: { one: "Summary", many: "Summaries" },
  blog: { one: "Article", many: "Articles" },
  podcast: { one: "Episode", many: "Episodes" },
};

export function isMediaKind(value: string): value is MediaKind {
  return (MEDIA_KINDS as readonly string[]).includes(value);
}

export function listMedia(
  params: { kind?: MediaKind | null; cursor?: string | null; limit?: number },
  signal?: AbortSignal,
): Promise<MediaPage> {
  return platformRequest<MediaPage>("/api/v1/media", {
    query: { kind: params.kind ?? undefined, cursor: params.cursor ?? undefined, limit: params.limit },
    signal,
  });
}

export function readMedia(slug: string, signal?: AbortSignal): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/${encodeURIComponent(slug)}`, { signal });
}

export type SearchHit = components["schemas"]["SearchHit"];

export function searchMedia(q: string, signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_SearchHit_"]>("/api/v1/media-search", {
    query: { q },
    signal,
  });
}

/**
 * The body of a media item.
 *
 * `content` is an open JSON object because the four kinds genuinely differ — a
 * deck has slides, an episode has an audio URL. Readers narrow it here rather
 * than casting at the point of use, so an item missing the field it needs
 * renders an explanation instead of throwing.
 */
export interface DeckSlide {
  title?: string;
  body?: string;
  image_url?: string;
}

export function deckSlides(item: MediaItem): DeckSlide[] {
  const slides = (item.content as { slides?: unknown }).slides;
  return Array.isArray(slides) ? (slides as DeckSlide[]) : [];
}

export function bodyMarkdown(item: MediaItem): string | null {
  const body = (item.content as { body_md?: unknown; body?: unknown }).body_md ??
    (item.content as { body?: unknown }).body;
  return typeof body === "string" ? body : null;
}

export function audioUrl(item: MediaItem): string | null {
  const url = (item.content as { audio_url?: unknown }).audio_url;
  return typeof url === "string" ? url : null;
}
