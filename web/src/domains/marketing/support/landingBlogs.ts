import { platformRequest, type components } from "@/foundation/platform-client";
import type { Blog } from "@/domains/marketing/support/blog";

type MediaPage = components["schemas"]["Page_MediaRead_"];

/**
 * The three most recent articles, for the landing page's blog rail.
 *
 * The retiring backend had a per-exam blog collection with its own approval
 * flag. Here an article is a published `media` item of kind `blog`, and
 * published *is* approved — a draft is 404 to everybody but an admin, so there
 * is nothing to filter client-side any more.
 */
export async function fetchLandingBlogs(limit = 3): Promise<Blog[]> {
  const page = await platformRequest<MediaPage>("/api/v1/media", {
    query: { kind: "blog", limit },
  });
  return page.items.map((item) => ({
    id: item.id,
    title: item.title,
    content: typeof item.content?.body_md === "string" ? item.content.body_md : "",
    created_at: item.published_at ?? "",
    approved: true,
    slug: item.slug,
  })) as unknown as Blog[];
}
