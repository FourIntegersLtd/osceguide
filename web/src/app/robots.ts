import type { MetadataRoute } from "next";
import { SITE_URL } from "@/app/metadata";
import { isProductionSiteUrl } from "@/foundation/config/siteUrl";
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
 *
 * On anything that is not the real production site — staging, or a Vercel
 * preview — this disallows everything instead. There is exactly one site
 * search engines should ever index; a preview or staging build ranking for
 * the same queries would split signal and can leak an unfinished page.
 *
 * `robotsFor` takes the site URL as an argument, rather than reading the
 * module-level `SITE_URL` directly, so a test can assert both branches with
 * literal values without mutating `process.env`.
 */
export function robotsFor(siteUrl: string): MetadataRoute.Robots {
  if (!isProductionSiteUrl(siteUrl)) {
    return { rules: { userAgent: "*", disallow: "/" } };
  }

  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [...PRIVATE_PATH_PREFIXES],
    },
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}

export default function robots(): MetadataRoute.Robots {
  return robotsFor(SITE_URL);
}
