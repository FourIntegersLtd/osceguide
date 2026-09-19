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

/** The backend's page cap. Asking for more is a 422, not a longer page. */
const MAX_PAGE = 100;
const MAX_PAGES = 6;

/**
 * Every published item of a kind, as one list.
 *
 * The A-to-Z groups by first letter and the deck sidebar shows every
 * presentation at once, so both need the whole set rather than a page of it —
 * the retiring client asked for `per_page=1000` and got away with it. This
 * walks the cursor instead, and stops at six pages so a library that grows
 * past six hundred items degrades into a long page rather than a hung screen.
 */
export async function listAllMedia(
  kind: MediaKind | null,
  signal?: AbortSignal,
): Promise<MediaItem[]> {
  const items: MediaItem[] = [];
  let cursor: string | null = null;

  for (let page = 0; page < MAX_PAGES; page += 1) {
    const result: MediaPage = await listMedia({ kind, cursor, limit: MAX_PAGE }, signal);
    items.push(...result.items);
    cursor = result.next_cursor ?? null;
    if (!cursor) break;
  }

  return items;
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

function field(item: MediaItem, ...names: string[]): unknown {
  const content = item.content as Record<string, unknown>;
  for (const name of names) {
    if (content[name] !== undefined && content[name] !== null) return content[name];
  }
  return undefined;
}

function stringField(item: MediaItem, ...names: string[]): string | null {
  const value = field(item, ...names);
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

function stringList(item: MediaItem, ...names: string[]): string[] {
  const value = field(item, ...names);
  return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === "string") : [];
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

/**
 * A deck may be a recorded presentation or a set of slides.
 *
 * The retiring client had both: `final_video_url` rendered a player and the
 * `slides` array was what the authoring tool wrote. Reading either keeps every
 * deck already published readable.
 */
export function deckVideoUrl(item: MediaItem): string | null {
  return stringField(item, "video_url", "final_video_url");
}

/** The "About" tab, which falls back to the list summary rather than sitting empty. */
export function aboutText(item: MediaItem): string | null {
  return stringField(item, "about") ?? (item.summary?.trim() ? item.summary : null);
}

/** A summary's podcast, which on the old client hung off the summary itself. */
export function podcastUrl(item: MediaItem): string | null {
  return stringField(item, "podcast_url", "audio_url");
}

export interface SummarySection {
  key: "red_flags" | "examinations" | "brief_management";
  items: string[];
}

/**
 * The three clinical sections of an A-to-Z summary.
 *
 * Returns an empty list when the item carries none of them, which is how a
 * summary published as plain markdown falls through to the prose reader
 * instead of rendering three empty cards.
 */
export function summarySections(item: MediaItem): SummarySection[] {
  const sections: SummarySection[] = [
    { key: "red_flags", items: stringList(item, "red_flags") },
    { key: "examinations", items: stringList(item, "examinations") },
    { key: "brief_management", items: stringList(item, "brief_management") },
  ];
  return sections.some((section) => section.items.length > 0) ? sections : [];
}

export function psychosocialAspects(item: MediaItem): string[] {
  return stringList(item, "psychosocial_aspects");
}

/**
 * The specialties an item is filed under.
 *
 * `MediaRead` has no specialty column, so this reads the authoring payload.
 * The facets it feeds hide themselves when nothing carries one — see
 * `docs/port-gaps.md`.
 */
export function specialtiesOf(item: MediaItem): string[] {
  const one = stringField(item, "specialty");
  const many = stringList(item, "specialties");
  return many.length > 0 ? many : one ? [one] : [];
}
