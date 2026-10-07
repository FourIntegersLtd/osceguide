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

/** Withdraws a published item to a draft, so it can be corrected or deleted. */
export function unpublishMedia(itemId: string): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/${encodeURIComponent(itemId)}/unpublish`, {
    method: "POST",
  });
}

/**
 * Frees an item a dead worker left locked in a running status. `/unlock` reaches the generated
 * types once openapi.json is regenerated; the route is declared by hand until then.
 */
export function unlockMedia(itemId: string): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/${encodeURIComponent(itemId)}/unlock`, {
    method: "POST",
  });
}

/** Stores a fact check a person did by hand, each claim with its source, in place of the platform's. */
export function recordHandCheck(
  itemId: string,
  claims: { claim: string; source: string; slide?: number | null }[],
): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/${encodeURIComponent(itemId)}/hand-check`, {
    method: "POST",
    body: { claims },
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

/** The title a generated draft gives itself: a deck calls it `topic`, a summary `name`. */
export function generatedTitle(generated: Record<string, unknown>): string {
  for (const key of ["title", "topic", "name"]) {
    const value = generated[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "";
}

export function generateBlog(prompt: string, examCode?: string | null) {
  return generateContent("/api/v1/platform/generate/blog", prompt, examCode);
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

/** Queues a check of the item's clinical claims against the guidelines. Changes no text. */
export function checkMediaFacts(itemId: string): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/${encodeURIComponent(itemId)}/check-facts`, {
    method: "POST",
  });
}

/** Queues writing (or, with `rewrite`, rewriting) what will be said, and checking it. Voices nothing. */
export function writeMediaScript(itemId: string, rewrite: boolean): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/${encodeURIComponent(itemId)}/write-script`, {
    method: "POST",
    body: { rewrite },
  });
}

/** Starts the agent that drafts, checks and fixes the item until it is ready to voice. Voices nothing. */
export function produceMedia(itemId: string, input: S["ProduceRequest"]): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/${encodeURIComponent(itemId)}/produce`, {
    method: "POST",
    body: input,
  });
}

/** Asks a running agent to stop after the step it is on. */
export function stopProduce(itemId: string): Promise<MediaItem> {
  return platformRequest<MediaItem>(`/api/v1/media/${encodeURIComponent(itemId)}/stop-produce`, {
    method: "POST",
  });
}
