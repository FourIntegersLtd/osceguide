/**
 * The one place platform-web reads its own public origin.
 *
 * Why this exists: staging (`staging.osceguide.com`) and every Vercel preview
 * build with `NODE_ENV=production`, exactly like the real production site. A
 * check written as `process.env.NODE_ENV === "production"` cannot tell any of
 * them apart — it was true on all three — so nothing here may read `NODE_ENV`
 * to decide "is this the live site?". `NEXT_PUBLIC_SITE_URL` is the value that
 * actually answers that question: production leaves it unset (so the default
 * below is production's own origin), staging sets it to
 * `https://staging.osceguide.com`, and a preview either leaves it unset or
 * points at its own preview URL — either way it is never production's.
 *
 * Every module that used to hardcode `https://osceguide.com` — the document
 * head, robots, the exam-subdomain resolver, the referral builder, the
 * marketing landing pages, the compliance pages' canonicals — reads it from
 * here instead, so there is exactly one place that knows the literal string.
 */

/** Production's own origin. The fallback when nothing else is configured. */
const PRODUCTION_SITE_URL = "https://osceguide.com";

/** Drop a trailing slash so every caller can safely append a path with `${SITE_URL}/foo`. */
function stripTrailingSlash(url: string): string {
  return url.replace(/\/+$/, "");
}

/**
 * This deployment's own public origin — e.g. `https://osceguide.com` in
 * production, `https://staging.osceguide.com` on staging, or a preview's own
 * `https://<branch>-<project>.vercel.app` when that is set for it.
 *
 * Read once, at module load, because the value is baked in at build time and
 * cannot change without a redeploy — the same reason `NEXT_PUBLIC_` variables
 * exist at all.
 */
export const SITE_URL: string = (() => {
  const configured = process.env.NEXT_PUBLIC_SITE_URL?.trim();
  return configured ? stripTrailingSlash(configured) : PRODUCTION_SITE_URL;
})();

/**
 * Whether a given site URL is exactly the real production site — never
 * staging, never a preview, no matter how close the string looks.
 *
 * Exported as a pure function (rather than only a boolean computed from
 * `SITE_URL`) so a test can assert it against a literal value without
 * mutating `process.env`, and so callers that already hold a site URL (for
 * example one read from a request) can ask the same question of it.
 */
export function isProductionSiteUrl(siteUrl: string): boolean {
  return siteUrl === PRODUCTION_SITE_URL;
}

/** Whether *this* deployment is the real production site. */
export const IS_PRODUCTION_SITE: boolean = isProductionSiteUrl(SITE_URL);

/**
 * The hostname of a site URL, lower-cased — e.g. `osceguide.com` or
 * `staging.osceguide.com`. Falls back to production's hostname if the URL is
 * somehow malformed, since a broken environment variable should degrade to
 * the safe, indexable default rather than throw during a page render.
 */
export function siteHostname(siteUrl: string): string {
  try {
    return new URL(siteUrl).hostname.toLowerCase();
  } catch {
    return new URL(PRODUCTION_SITE_URL).hostname;
  }
}

/** This deployment's own hostname, derived from `SITE_URL`. */
export const SITE_HOSTNAME: string = siteHostname(SITE_URL);
