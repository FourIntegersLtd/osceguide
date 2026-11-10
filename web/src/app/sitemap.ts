import type { MetadataRoute } from "next";
import { SITE_URL } from "@/app/metadata";
import { blogPath } from "@/capabilities/media/blogs";
import { listAllBlogs } from "@/capabilities/media/blogsServer";
import { PUBLIC_MARKETING_PATHS } from "@/foundation/routing/pathVisibility";
import { HIDDEN_EXAM_PATHS } from "@/domains/marketing/site/siteLinks";

/**
 * The pages worth indexing.
 *
 * Built from `PUBLIC_MARKETING_PATHS`, which is also what the robots file
 * stands on the other side of — one list of what is public, read two ways.
 * `next-sitemap` crawled the route tree instead and published whatever it
 * found, including the back office; see the note on that list.
 */
function priorityFor(path: string): number {
  if (path === "") return 1;
  if (path.startsWith("/exams/")) return 0.9;
  if (path.startsWith("/compliances/")) return 0.3;
  return 0.8;
}

// Hourly, so a new post reaches the sitemap without a deploy.
export const revalidate = 3600;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const pages = PUBLIC_MARKETING_PATHS
    // `/exams/classic` is the homepage again, and canonicalises to it.
    .filter((path) => path !== "/exams/classic" && !HIDDEN_EXAM_PATHS.includes(path))
    .map((path) => ({
      url: `${SITE_URL}${path}`,
      changeFrequency: "weekly" as const,
      priority: priorityFor(path),
    }));
  const posts = (await listAllBlogs()).map((post) => ({
    url: `${SITE_URL}${blogPath(post.slug)}`,
    lastModified: post.updated_at,
    changeFrequency: "monthly" as const,
    priority: 0.7,
  }));
  return [...pages, ...posts];
}
