import { platformRequest, type components } from "@/foundation/platform-client";
import type { MediaKind } from "@/capabilities/media/api";

type S = components["schemas"];

export type MediaItem = S["app__features__media__schemas__MediaRead"];
export type CreateMediaInput = S["CreateMedia"];
export type UpdateMediaInput = S["UpdateMedia"];
type MediaPage = S["MediaPage"];

type GenerateResult = S["GenerateResult"];

const MAX_PAGE = 100;

export function createMedia(input: CreateMediaInput): Promise<MediaItem> {
  return platformRequest<MediaItem>("/api/v1/media", { method: "POST", body: input });
}

export function updateMedia(itemId: string, changes: UpdateMediaInput): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/${encodeURIComponent(itemId)}`, {
    method: "PATCH",
    body: changes,
  });
}

export function publishMedia(itemId: string): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/${encodeURIComponent(itemId)}/publish`, {
    method: "POST",
  });
}

export function readMediaById(itemId: string, signal?: AbortSignal): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/by-id/${encodeURIComponent(itemId)}`, { signal });
}

export function deleteMedia(itemId: string): Promise<void> {
  return platformRequest<void>(`/api/v1/media/${encodeURIComponent(itemId)}`, { method: "DELETE" });
}

/** One page's worth of a page-size default for the authoring table. */
export const AUTHORING_MEDIA_PAGE_LIMIT = MAX_PAGE;

/**
 * One page of a kind's rows, draft and published, for the authoring table.
 *
 * Used to walk every cursor up front so the table could filter by exam and
 * search box text in the browser. `exam_code` and `q` now do that in SQL, so
 * this asks for one page at a time instead — `useCursorPages` grows the list
 * as the table asks for more.
 */
export function listMediaForAuthoring(
  kind: MediaKind,
  params: { cursor?: string | null; limit?: number; examCode?: string | null; q?: string | null } = {},
  signal?: AbortSignal,
): Promise<MediaPage> {
  return platformRequest("/api/v1/media", {
    signal,
    query: {
      kind,
      limit: params.limit ?? MAX_PAGE,
      status: "all",
      cursor: params.cursor ?? undefined,
      exam_code: params.examCode ?? undefined,
      q: params.q ?? undefined,
    },
  });
}

async function generateContent(
  path: string,
  prompt: string,
  examCode?: string | null,
): Promise<Record<string, unknown>> {
  const result = await platformRequest<GenerateResult>(path, {
    method: "POST",
    body: { prompt, exam_code: examCode ?? null },
  });
  const content = result.content;
  if (content && typeof content === "object" && !Array.isArray(content)) {
    return content as Record<string, unknown>;
  }
  return {};
}

export function generateSummary(prompt: string, examCode?: string | null) {
  return generateContent("/api/v1/platform/generate/summary", prompt, examCode);
}

export function generateBlog(prompt: string, examCode?: string | null) {
  return generateContent("/api/v1/platform/generate/blog", prompt, examCode);
}

export function generateSlideDeck(prompt: string, examCode?: string | null) {
  return generateContent("/api/v1/platform/generate/slide-deck", prompt, examCode);
}

export function generatePodcast(prompt: string, examCode?: string | null) {
  return generateContent("/api/v1/platform/generate/podcast", prompt, examCode);
}

export function generateSummaryPodcast(itemId: string): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/${encodeURIComponent(itemId)}/generate-podcast`, {
    method: "POST",
  });
}

export function regenerateSlideAv(itemId: string): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/${encodeURIComponent(itemId)}/regenerate-av`, {
    method: "POST",
  });
}

export function generatePodcastAudio(itemId: string): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/${encodeURIComponent(itemId)}/generate-audio`, {
    method: "POST",
  });
}
