import { hasStoredSession, platformRequest, type components } from "@/foundation/platform-client";
import type { Blog } from "@/domains/marketing/support/blog";

type MediaPage = components["schemas"]["Page_MediaRead_"];

/**
 * The three most recent articles, for the landing page's blog rail.
 *
 * The retiring backend had a per-exam blog collection with its own approval
 * flag. Here an article is a published `media` item of kind `blog`, and
 * published *is* approved — a draft is 404 to everybody but an admin, so there
 * is nothing to filter client-side any more.
 *
 * `GET /media` requires a bearer token, so a signed-out visitor — which is
 * most visitors to a landing page — cannot read this at all. Rather than ask
 * and take a 401 on the busiest public page, we do not ask: the rail hides
 * itself on an empty answer, which is the same thing it did on a failure. A
 * public blog listing is in `docs/port-gaps.md`.
 */
export async function fetchLandingBlogs(limit = 3): Promise<Blog[]> {
  if (!hasStoredSession()) return [];
  const page = await platformRequest<MediaPage>("/api/v1/media", {
    query: { kind: "blog", limit },
  }).catch(() => null);
  if (!page) return [];
  return page.items.map((item) => ({
    id: item.id,
    title: item.title,
    content: typeof item.content?.body_md === "string" ? item.content.body_md : "",
    created_at: item.published_at ?? "",
    approved: true,
    slug: item.slug,
  })) as unknown as Blog[];
}
