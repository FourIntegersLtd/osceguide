import type { MetadataRoute } from "next";
import { SITE_URL } from "@/app/metadata";
import { PUBLIC_MARKETING_PATHS } from "@/foundation/routing/pathVisibility";

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

export default function sitemap(): MetadataRoute.Sitemap {
  const today = new Date();
  return PUBLIC_MARKETING_PATHS.map((path) => ({
    url: `${SITE_URL}${path}`,
    lastModified: today,
    changeFrequency: "weekly" as const,
    priority: priorityFor(path),
  }));
}
