import { platformRequest } from "@/foundation/platform-client";
import { removePost, type Post, type PostPage } from "@/capabilities/community/api";

export type ModerationPost = Post;

export function listModerationPosts(
  params: { days?: number; limit?: number } = {},
  signal?: AbortSignal,
): Promise<PostPage> {
  return platformRequest<PostPage>("/api/v1/platform/moderation/posts", {
    signal,
    query: { days: params.days ?? 7, limit: params.limit ?? 100 },
  });
}

export function deleteModerationPost(postId: string): Promise<void> {
  return removePost(postId);
}
