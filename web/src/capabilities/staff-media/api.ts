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

export function listMediaForAuthoring(
  kind: MediaKind,
  signal?: AbortSignal,
): Promise<MediaPage> {
  return platformRequest("/api/v1/media", {
    signal,
    query: { kind, limit: MAX_PAGE, status: "all" },
  });
}

/** Walk the cursor until every draft and published row of a kind is loaded. */
export async function listAllMediaForAuthoring(
  kind: MediaKind,
  signal?: AbortSignal,
): Promise<MediaItem[]> {
  const items: MediaItem[] = [];
  let cursor: string | null = null;

  for (;;) {
    const page: MediaPage = await platformRequest("/api/v1/media", {
      signal,
      query: { kind, limit: MAX_PAGE, status: "all", cursor },
    });
    items.push(...page.items);
    cursor = page.next_cursor ?? null;
    if (!cursor) break;
  }

  return items;
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
