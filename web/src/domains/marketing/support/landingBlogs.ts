import { platformRequest, type components } from "@/foundation/platform-client";
import type { Blog } from "@/domains/marketing/support/blog";

type MediaPage = components["schemas"]["MediaPage"];
type MediaItem = components["schemas"]["app__features__media__schemas__MediaRead"];

function bodyOf(item: MediaItem): string {
  const body = item.content?.body_md;
  return typeof body === "string" ? body : "";
}

/**
 * The most recent articles, for the landing page's blog rail.
 *
 * The retiring backend had a per-exam blog collection with its own approval
 * flag, newest first. Here an article is a published `media` item of kind
 * `blog`, and published *is* approved — a draft is 404 to everybody but an
 * admin, so there is nothing to filter client-side any more. `GET /media`
 * pages newest-first on `created_at`, which is the rail's order.
 *
 * `GET /media` is public — it answers an anonymous caller with the published
 * catalogue — so the signed-out visitor, who is most visitors to a landing
 * page, gets the rail too. A failure still degrades to an empty list, which
 * hides the section rather than putting a hole in the page.
 */
export async function fetchLandingBlogs(limit = 3): Promise<Blog[]> {
  const page = await platformRequest<MediaPage>("/api/v1/media", {
    query: { kind: "blog", limit },
  }).catch(() => null);
  if (!page) return [];
  return page.items.map((item) => ({
    id: item.id,
    blog_id: item.id,
    title: item.title,
    content: bodyOf(item),
    created_at: item.published_at ?? "",
    approved: true,
    // The rail links to `/blogs/<url>`; the media item's slug is the address.
    url: item.slug,
  }));
}
