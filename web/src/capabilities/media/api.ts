import { platformRequest, type components } from "@/foundation/platform-client";
import { b2cDeckSlides } from "@/capabilities/media/b2cDeckSlides";

export type MediaItem =
  components["schemas"]["app__features__media__schemas__MediaRead"];
export type MediaPage = components["schemas"]["MediaPage"];

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
  params: {
    kind?: MediaKind | null;
    cursor?: string | null;
    limit?: number;
    /** Narrow to one exam. The server keeps unexamined material, which is free material. */
    examCode?: string | null;
    /** Matched against title and summary, in SQL rather than in the browser. */
    q?: string | null;
  },
  signal?: AbortSignal,
): Promise<MediaPage> {
  return platformRequest<MediaPage>("/api/v1/media", {
    query: {
      kind: params.kind ?? undefined,
      cursor: params.cursor ?? undefined,
      limit: params.limit,
      exam_code: params.examCode ?? undefined,
      q: params.q ?? undefined,
    },
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

/**
 * Everything matching a filter, with the filtering done by the server.
 *
 * `listAllMedia` walks the whole catalogue and leaves the caller to narrow it,
 * which was the only option when `GET /media` took `kind` and nothing else. It
 * takes `exam_code` and `q` now, so a search that used to pull six pages down to
 * match one word against them asks for the matches instead — and stops being
 * wrong about a library bigger than six hundred items, which is the failure the
 * page cap was hiding.
 */
export async function listMatchingMedia(
  params: { kind?: MediaKind | null; examCode?: string | null; q?: string | null },
  signal?: AbortSignal,
): Promise<MediaItem[]> {
  const items: MediaItem[] = [];
  let cursor: string | null = null;

  for (let page = 0; page < MAX_PAGES; page += 1) {
    const result = await listMedia(
      {
        kind: params.kind ?? null,
        examCode: params.examCode ?? null,
        q: params.q ?? null,
        cursor,
        limit: MAX_PAGE,
      },
      signal,
    );
    items.push(...result.items);
    cursor = result.next_cursor ?? null;
    if (!cursor) break;
  }

  return items;
}

function normalizeMediaSlug(slug: string): string {
  const trimmed = slug.trim();
  if (!trimmed) return trimmed;
  try {
    return decodeURIComponent(trimmed);
  } catch {
    return trimmed;
  }
}

export function readMedia(slug: string, signal?: AbortSignal): Promise<MediaItem> {
  const normalized = normalizeMediaSlug(slug);
  return platformRequest<MediaItem>("/api/v1/media/lookup", {
    query: { slug: normalized },
    signal,
  });
}

export type SearchHit = components["schemas"]["SearchHit"];
export type MediaSearchPage = components["schemas"]["MediaSearchPage"];

/**
 * The server's own search: `q`, an optional `kind`, and a real cursor.
 *
 * Paging is keyset over `(score, id)` and bounded to the index's top hundred
 * hits, because the vector index answers with a limit and nothing else — there
 * is no page 101, and that slice's README says so rather than hiding it behind
 * an offset.
 */
export function searchMedia(
  q: string,
  options: { kind?: MediaKind | null; cursor?: string | null } = {},
  signal?: AbortSignal,
): Promise<MediaSearchPage> {
  return platformRequest<MediaSearchPage>("/api/v1/media-search", {
    query: {
      q,
      kind: options.kind ?? undefined,
      cursor: options.cursor ?? undefined,
    },
    signal,
  });
}

/**
 * Substring hits, for when the vector search has nothing to say.
 *
 * An empty index, a missing key, or a catalogue nobody has embedded yet all
 * answer with no hits — and "no results" for a word that is plainly in a title
 * is a failure, not the retiring A-to-Z's behaviour. The *matching* now asks the
 * server, since `q` on `GET /media` is an ILIKE over title and summary; what is
 * left here is only the body match the server does not attempt.
 */
function substringSearchHits(items: MediaItem[], normalized: string): SearchHit[] {
  return items
    .filter((item) => {
      const body = bodyMarkdown(item);
      const haystack = `${item.title} ${item.summary ?? ""} ${body ?? ""}`.toLowerCase();
      return haystack.includes(normalized);
    })
    .slice(0, 20)
    .map((item) => ({
      id: item.id,
      kind: item.kind,
      slug: item.slug,
      title: item.title,
      score: 1,
      // A real hit carries the server's excerpt; a synthesized one still has to
      // say something, and the summary is what it has.
      excerpt: item.summary ?? item.title,
    }));
}

export async function searchMediaWithFallback(
  q: string,
  options: { examCode?: string | null; kind?: MediaKind | null } = {},
  signal?: AbortSignal,
): Promise<MediaSearchPage> {
  const trimmed = q.trim();
  const normalized = trimmed.toLowerCase();
  if (!normalized) return { items: [], next_cursor: null, total_count: 0 };

  const kind = options.kind ?? null;
  const examCode = options.examCode ?? null;

  /*
   * Whole-catalogue search is the vector index's job, and it now answers with an
   * excerpt, a total and a cursor of its own. It cannot narrow by exam — a hit
   * carries no exam code — so that path stays unfiltered, as it always was. The
   * substring fallback does narrow, because a catalogue item carries one.
   */
  if (!kind) {
    try {
      const page = await searchMedia(trimmed, {}, signal);
      if (page.items.length > 0) return page;
    } catch {
      // A search that could not run is not a search that found nothing.
    }
  }

  const matches = await listMatchingMedia({ kind, examCode, q: trimmed }, signal);
  return {
    items: substringSearchHits(matches, normalized),
    next_cursor: null,
    total_count: matches.length,
  };
}

/** Items for the current exam, like the old client scoped lists by `app_type`. */
export function filterMediaByExam(items: MediaItem[], examCode: string | null): MediaItem[] {
  if (!examCode) return items;
  const code = examCode.toLowerCase();
  return items.filter((item) => !item.exam_code || item.exam_code.toLowerCase() === code);
}

/**
 * The episodes the player should actually offer.
 *
 * The page item is read by slug (body included for staff and subscribers). The
 * playlist is `GET /media?kind=podcast`, which can omit this row (a cursor that
 * skips same-timestamp imports) or strip `content` (a listing that locked the
 * body). Overlay the page item so the episode you opened still has its URL,
 * then drop rows with no audio so the playlist is not 101 silent slots.
 */
export function podcastSeries(
  listed: MediaItem[],
  pageItem: MediaItem,
  examCode: string | null,
): MediaItem[] {
  const scoped = filterMediaByExam(listed, examCode);
  const merged = scoped.map((entry) =>
    entry.id === pageItem.id && audioUrl(entry) === null ? pageItem : entry,
  );
  if (!merged.some((entry) => entry.id === pageItem.id)) {
    merged.unshift(pageItem);
  }
  const withAudio = merged.filter((entry) => audioUrl(entry) !== null);
  return withAudio.length > 0 ? withAudio : [pageItem];
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

function contentRecord(item: MediaItem): Record<string, unknown> {
  const raw = item.content;
  if (raw && typeof raw === "object" && !Array.isArray(raw)) {
    return raw as Record<string, unknown>;
  }
  return {};
}

function field(item: MediaItem, ...names: string[]): unknown {
  const content = contentRecord(item);
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
  const content = contentRecord(item);
  const slides = content.slides;
  if (!Array.isArray(slides) || slides.length === 0) return [];
  return b2cDeckSlides(content);
}

export function bodyMarkdown(item: MediaItem): string | null {
  const content = contentRecord(item);
  const body = content.body_md ?? content.body;
  return typeof body === "string" ? body : null;
}

export function audioUrl(item: MediaItem): string | null {
  return stringField(item, "audio_url", "podcast_url");
}

/** Sidebar grouping for the podcast tab when items lack a dedicated series field. */
export function podcastGroupLabel(item: MediaItem): string {
  return (
    stringField(item, "series_title", "series", "show_name") ??
    (item.exam_code ? item.exam_code.toUpperCase() : null) ??
    "Episodes"
  );
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
  return (
    stringField(item, "about") ??
    stringField(item, "topic") ??
    (item.summary?.trim() ? item.summary : null)
  );
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
 * Whether this summary uses the B2C A-to-Z shape (lists in `content`), not
 * plain markdown only.
 */
export function isStructuredSummary(item: MediaItem): boolean {
  const content = contentRecord(item);
  return (
    "red_flags" in content ||
    "examinations" in content ||
    "brief_management" in content ||
    "psychosocial_aspects" in content ||
    podcastUrl(item) !== null
  );
}

/**
 * The three clinical sections of an A-to-Z summary.
 *
 * On the retiring client the detail page always drew three cards (Red flags,
 * Examinations, Management) even when a list was empty. When the payload is
 * structured, all three are returned; otherwise an empty list falls through to
 * the prose reader.
 */
export function summarySections(item: MediaItem): SummarySection[] {
  const sections: SummarySection[] = [
    { key: "red_flags", items: stringList(item, "red_flags") },
    { key: "examinations", items: stringList(item, "examinations") },
    { key: "brief_management", items: stringList(item, "brief_management") },
  ];
  if (isStructuredSummary(item)) return sections;
  return sections.some((section) => section.items.length > 0) ? sections : [];
}

export function psychosocialAspects(item: MediaItem): string[] {
  return stringList(item, "psychosocial_aspects");
}

/**
 * The specialties an item is filed under.
 *
 * Reads the authoring payload (`content`), not `MediaRead.specialty`: the
 * content payload is what authors set and what the whole library was tagged
 * through, so it is the source that has data behind it. `MediaRead` does now
 * carry a root `specialty` column (see `openapi.json`), but nothing in the
 * porting wrote to it, and the facets these feed hide themselves when nothing
 * carries one — see `docs/port-gaps.md`.
 */
export function specialtiesOf(item: MediaItem): string[] {
  const one = stringField(item, "specialty");
  const many = stringList(item, "specialties");
  return many.length > 0 ? many : one ? [one] : [];
}

/**
 * Blog/document "updated" stamp, read off the authoring payload.
 *
 * B2C stored it on the document; `MediaRead` also has a root `updated_at`
 * now, but it is not what these screens were built against, so the payload
 * stays the source. See also `specialtiesOf`.
 */
export function contentUpdatedAt(item: MediaItem): string | null {
  return stringField(item, "updated_at");
}

/** Slide list rows on the retiring client showed `slides_count` from Firestore. */
export function deckSlidesCount(item: MediaItem): number | null {
  const raw = field(item, "slides_count");
  if (typeof raw === "number" && Number.isFinite(raw) && raw >= 0) return raw;
  const slides = deckSlides(item);
  return slides.length > 0 ? slides.length : null;
}
