import { platformRequest, type components } from "@/foundation/platform-client";
import type { CommunityCategory } from "@/capabilities/community/discussionModel";

export type Post = components["schemas"]["app__features__community__schemas__PostRead"];
export type Visibility = components["schemas"]["Visibility"];
// `___1` is the marketplace's page of slots; community's is `___2`. The
// generator numbers same-named models by order, so this alias exists to be
// the one place that has to be right.
export type PostPage = components["schemas"]["app__core__pagination__Page_PostRead___2"];

/** Who a post is addressed to, as this capability passes it around. */
export interface Room {
  visibility: Visibility;
  orgId: string | null;
}

export const PUBLIC_ROOM: Room = { visibility: "public", orgId: null };

/**
 * Questions and replies.
 *
 * One `posts` table with a self-referencing parent, and an `audience` that is
 * public, an organisation or a group. That audience is why this is a
 * capability rather than a consumer feature: an institution's trainees get
 * their own cohort discussion from the same screens, scoped by the backend.
 *
 * A list with no audience spans the public pool *and* every room the caller is
 * in, which is the right answer for somebody's own workspace. An
 * organisation's workspace narrows it to that organisation, so a cohort's
 * conversation never mixes with the public board.
 */
export function listQuestions(
  params: {
    room?: Room | null;
    cursor?: string | null;
    limit?: number;
    mine?: boolean;
    tag?: string | null;
    examCode?: string | null;
    category?: CommunityCategory | null;
  },
  signal?: AbortSignal,
): Promise<PostPage> {
  const room = params.room ?? null;
  const scoped = room !== null && room.visibility !== "public";
  const tag = params.tag?.trim();
  return platformRequest<PostPage>("/api/v1/community/questions", {
    query: {
      visibility: scoped ? room.visibility : undefined,
      audience_org_id: scoped ? (room.orgId ?? undefined) : undefined,
      cursor: params.cursor ?? undefined,
      limit: params.limit ?? undefined,
      // Narrowed in SQL. Filtering the fetched page would make the tab mean
      // "the first hundred questions, minus the ones that were not mine".
      mine: params.mine ? true : undefined,
      // One specialty. The route refuses to widen the room; it only narrows it.
      tag: tag ? tag : undefined,
      // The exam tab: the route resolves the code and narrows the same way.
      exam_code: params.examCode ? params.examCode : undefined,
      category: params.category ? params.category : undefined,
    },
    signal,
  });
}

/**
 * One question by id.
 *
 * A thread used to be found by searching the page the feed already served, so a
 * question older than the first hundred opened as "Question not found" — the
 * same shape as `findLibraryStation`, and the reason a deep link must not
 * depend on how much other traffic there happens to be.
 */
export function readQuestion(questionId: string, signal?: AbortSignal): Promise<Post> {
  return platformRequest<Post>(
    `/api/v1/community/questions/${encodeURIComponent(questionId)}`,
    { signal },
  );
}

/** Everything this person has answered, across every question. */
export function listMyAnswers(
  params: { cursor?: string | null; limit?: number } = {},
  signal?: AbortSignal,
): Promise<PostPage> {
  return platformRequest<PostPage>("/api/v1/community/replies", {
    query: { author: "me", cursor: params.cursor ?? undefined, limit: params.limit ?? undefined },
    signal,
  });
}

export function askQuestion(input: {
  title: string;
  body: string;
  examCode?: string | null;
  category?: CommunityCategory;
  tags?: readonly string[];
  room?: Room;
}): Promise<Post> {
  const room = input.room ?? PUBLIC_ROOM;
  return platformRequest<Post>("/api/v1/community/questions", {
    method: "POST",
    body: {
      title: input.title,
      body: input.body,
      exam_code: input.examCode ?? null,
      category: input.category ?? "general",
      // The backend normalises (trim, lowercase, de-dupe) and caps the count,
      // so the keys go up as chosen and an over-long or over-many selection
      // comes back as a refusal the composer surfaces.
      tags: input.tags ? [...input.tags] : [],
      audience: { visibility: room.visibility, org_id: room.orgId },
    },
  });
}

export function listReplies(questionId: string, signal?: AbortSignal): Promise<PostPage> {
  return platformRequest<PostPage>(
    `/api/v1/community/questions/${encodeURIComponent(questionId)}/replies`,
    { signal },
  );
}

/** A reply inherits its question's audience, so it is never given one here. */
export function reply(questionId: string, body: string): Promise<Post> {
  return platformRequest<Post>(
    `/api/v1/community/questions/${encodeURIComponent(questionId)}/replies`,
    { method: "POST", body: { body } },
  );
}

/**
 * A like is a row, so this is idempotent per person, and the post it answers
 * with carries the authoritative count.
 *
 * The consumer backend incremented a counter, which meant a double tap counted
 * twice and nothing could be un-liked.
 */
export function like(postId: string): Promise<Post> {
  return platformRequest<Post>(`/api/v1/community/posts/${encodeURIComponent(postId)}/like`, {
    method: "POST",
  });
}

export function unlike(postId: string): Promise<Post> {
  return platformRequest<Post>(`/api/v1/community/posts/${encodeURIComponent(postId)}/like`, {
    method: "DELETE",
  });
}

export function removePost(postId: string): Promise<void> {
  return platformRequest<void>(`/api/v1/community/posts/${encodeURIComponent(postId)}`, {
    method: "DELETE",
  });
}

/**
 * Comments on one station.
 *
 * The same `posts` table, a `comment` kind and a station id — which is why the
 * old client's separate comments collection is this file rather than another
 * one. Audience-filtered like everything else here, so an institution's notes
 * on a station stay inside the institution.
 */
export function listStationComments(stationId: string, signal?: AbortSignal): Promise<PostPage> {
  return platformRequest<PostPage>(
    `/api/v1/stations/${encodeURIComponent(stationId)}/comments`,
    { signal },
  );
}

export function commentOnStation(stationId: string, body: string, room: Room = PUBLIC_ROOM): Promise<Post> {
  return platformRequest<Post>(`/api/v1/stations/${encodeURIComponent(stationId)}/comments`, {
    method: "POST",
    body: { body, audience: { visibility: room.visibility, org_id: room.orgId } },
  });
}
