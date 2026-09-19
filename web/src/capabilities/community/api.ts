import { platformRequest, type components } from "@/foundation/platform-client";

export type Post = components["schemas"]["app__features__community__schemas__PostRead"];
export type Visibility = components["schemas"]["Visibility"];
// `___1` is the marketplace's page of slots; community's is `___2`. The
// generator numbers same-named models by order, so this alias exists to be
// the one place that has to be right.
export type PostPage = components["schemas"]["app__core__pagination__Page_PostRead___2"];

/**
 * Questions and replies.
 *
 * One `posts` table with a self-referencing parent, and an `audience` that is
 * public, an organisation or a group. That audience is why this is a
 * capability rather than a consumer feature: an institution's trainees get
 * their own cohort discussion from the same screens, scoped by the backend.
 */
export function listQuestions(
  params: { visibility?: Visibility | null; orgId?: string | null; cursor?: string | null },
  signal?: AbortSignal,
): Promise<PostPage> {
  return platformRequest<PostPage>("/api/v1/community/questions", {
    query: {
      visibility: params.visibility ?? undefined,
      audience_org_id: params.orgId ?? undefined,
      cursor: params.cursor ?? undefined,
    },
    signal,
  });
}

export function askQuestion(input: {
  title: string;
  body: string;
  examCode?: string | null;
  visibility?: Visibility;
  orgId?: string | null;
}): Promise<Post> {
  return platformRequest<Post>("/api/v1/community/questions", {
    method: "POST",
    body: {
      title: input.title,
      body: input.body,
      exam_code: input.examCode ?? null,
      audience: {
        visibility: input.visibility ?? "public",
        org_id: input.orgId ?? null,
      },
    },
  });
}

export function listReplies(questionId: string, signal?: AbortSignal): Promise<PostPage> {
  return platformRequest<PostPage>(
    `/api/v1/community/questions/${encodeURIComponent(questionId)}/replies`,
    { signal },
  );
}

export function reply(questionId: string, body: string): Promise<Post> {
  return platformRequest<Post>(
    `/api/v1/community/questions/${encodeURIComponent(questionId)}/replies`,
    { method: "POST", body: { body } },
  );
}

/**
 * A like is a row, so this is idempotent per person.
 *
 * The consumer backend incremented a counter, which meant a double tap counted
 * twice and nothing could be un-liked.
 */
export function like(postId: string): Promise<void> {
  return platformRequest<void>(`/api/v1/community/posts/${encodeURIComponent(postId)}/like`, {
    method: "POST",
  });
}

export function unlike(postId: string): Promise<void> {
  return platformRequest<void>(`/api/v1/community/posts/${encodeURIComponent(postId)}/like`, {
    method: "DELETE",
  });
}

export function removePost(postId: string): Promise<void> {
  return platformRequest<void>(`/api/v1/community/posts/${encodeURIComponent(postId)}`, {
    method: "DELETE",
  });
}
