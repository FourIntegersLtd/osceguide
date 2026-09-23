import type { MetadataRoute } from "next";
import { SITE_URL } from "@/app/metadata";
import { PRIVATE_PATH_PREFIXES } from "@/foundation/routing/pathVisibility";

/**
 * What a crawler may read.
 *
 * `frontend/public/robots.txt` was a hand-maintained file listing the old
 * client's paths — `/admin/`, `/auth/`, `/mocks/` — most of which are not
 * addresses here at all. Same intent, real route tree: the marketing surface is
 * public, and everything that needs a session is not.
 *
 * The list comes from `foundation/routing`, which is also what `RequireSession`
 * guards, so the two cannot disagree about what is private.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [...PRIVATE_PATH_PREFIXES],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
