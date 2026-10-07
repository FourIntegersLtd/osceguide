import { platformRequest } from "@/foundation/platform-client";
import { removePost, type Post, type PostPage } from "@/capabilities/community/api";

/**
 * A post as the moderation queue lists it. `station_id` (the station a comment is on) reaches the
 * generated `Post` once openapi.json is regenerated; until then it is declared here.
 */
export type ModerationPost = Post & { station_id?: string | null };

export const MODERATION_PAGE_LIMIT = 25;

export function listModerationPosts(
  params: { days?: number; cursor?: string | null } = {},
  signal?: AbortSignal,
): Promise<PostPage> {
  return platformRequest<PostPage>("/api/v1/platform/moderation/posts", {
    signal,
    query: {
      days: params.days ?? 7,
      limit: MODERATION_PAGE_LIMIT,
      cursor: params.cursor || undefined,
    },
  });
}

export function deleteModerationPost(postId: string): Promise<void> {
  return removePost(postId);
}
