import { cache } from "react";
import { PlatformError, PlatformTransportError } from "@/foundation/platform-client";
import { renderMarkdownToSafeHtml } from "@/foundation/ui/renderMarkdown";
import { bodyMarkdown, listMedia, readMedia, type MediaItem, type MediaPage } from "@/capabilities/media/api";
import { BLOG_PAGE_SIZE, SITEMAP_PAGE_SIZE } from "@/capabilities/media/blogs";

/**
 * What the public blog pages read on the server, for the HTML a crawler gets.
 * The media routes are public (`MaybePrincipal`, and a blog is never locked),
 * so no session is needed.
 */

/** The api answered with an error or could not be reached; anything else is a bug and propagates. */
function isApiFailure(cause: unknown): boolean {
  return cause instanceof PlatformError || cause instanceof PlatformTransportError;
}

/** One post and its body as sanitised HTML, or null when there is no such published post. Read once per request. */
export const readBlogPost = cache(async (slug: string): Promise<{ item: MediaItem; bodyHtml: string } | null> => {
  let item: MediaItem;
  try {
    item = await readMedia(slug);
  } catch (cause) {
    if (cause instanceof PlatformError && cause.status === 404) return null;
    throw cause;
  }
  if (item.kind !== "blog") return null;
  return { item, bodyHtml: await renderMarkdownToSafeHtml(bodyMarkdown(item) ?? "") };
});

/** The first page of the blogs index, as `BlogIndex` would load it. A failure is an empty seed: the browser asks again. */
export async function readFirstBlogPage(examCode: string | null): Promise<MediaPage | undefined> {
  try {
    return await listMedia({ kind: "blog", limit: BLOG_PAGE_SIZE, examCode, sort: "published" });
  } catch (cause) {
    if (isApiFailure(cause)) return undefined;
    throw cause;
  }
}

/** Every published blog, newest first, for the sitemap. An api failure is an empty list. */
export async function listAllBlogs(): Promise<MediaItem[]> {
  const posts: MediaItem[] = [];
  try {
    let cursor: string | null = null;
    do {
      const page: MediaPage = await listMedia({ kind: "blog", cursor, limit: SITEMAP_PAGE_SIZE, sort: "published" });
      posts.push(...page.items);
      cursor = page.next_cursor ?? null;
    } while (cursor);
  } catch (cause) {
    // A failed walk gives the sitemap the posts read so far rather than none.
    if (isApiFailure(cause)) return posts;
    throw cause;
  }
  return posts;
}
