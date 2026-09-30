import { SITE_URL, siteHostname } from "@/foundation/config/siteUrl";

/**
 * Local dev's own base domain, always available regardless of which site
 * this deployment answers to — `sca.lvh.me` keeps working whether
 * `NEXT_PUBLIC_SITE_URL` is unset (production), or set to staging's origin.
 */
const LOCAL_BASE_DOMAIN = "lvh.me";

/** Subdomains that are never an exam, however they show up in a host header. */
const IGNORED_SUBDOMAINS = new Set(["www", ""]);

/**
 * Pick the exam subdomain out of `hostname`, relative to one candidate base
 * domain — e.g. with base domain `osceguide.com`, `sca.osceguide.com` yields
 * `"sca"` and the bare `osceguide.com` yields `null`.
 */
function examFromHostname(hostname: string, baseDomain: string): string | null {
  if (hostname === baseDomain || hostname === `www.${baseDomain}`) {
    return null;
  }
  if (!hostname.endsWith(baseDomain)) {
    return null;
  }
  const labels = hostname.split(".");
  const baseLabelsCount = baseDomain.split(".").length;
  if (labels.length <= baseLabelsCount) {
    return null;
  }
  const subdomain = labels[0];
  if (!subdomain || IGNORED_SUBDOMAINS.has(subdomain)) {
    return null;
  }
  return subdomain;
}

/**
 * Which exam subdomain, if any, `host` names — relative to `siteBaseDomain`,
 * the hostname of the site this particular deployment answers to.
 *
 * Exam subdomains are always relative to *this deployment's own* site host,
 * never to production's literal string: `sca.osceguide.com` names an exam
 * only in production (where the site host is `osceguide.com`), and
 * `sca.staging.osceguide.com` names that same exam on staging (where the
 * site host is `staging.osceguide.com`). The bare `staging.osceguide.com`
 * must never be read as an exam called "staging" — it *is* the site host,
 * so `examFromHostname` returns `null` for it before any subdomain split
 * happens.
 *
 * Exported (rather than folding this into `getExamFromHost`) so a test can
 * assert literal expected values for every deployment shape — production,
 * staging, a preview — without touching `process.env`.
 */
export function examFromHostAndSite(
  host: string | null | undefined,
  siteBaseDomain: string,
): string | null {
  if (!host) {
    return null;
  }
  const hostname = host.split(":")[0]?.toLowerCase();
  if (!hostname) {
    return null;
  }

  const bySite = examFromHostname(hostname, siteBaseDomain);
  if (bySite) {
    return bySite;
  }

  // Local dev's base domain is checked independently of the site host, so it
  // still resolves whether this deployment thinks it is production or staging.
  if (siteBaseDomain !== LOCAL_BASE_DOMAIN) {
    return examFromHostname(hostname, LOCAL_BASE_DOMAIN);
  }
  return null;
}

/**
 * Which exam subdomain, if any, a request's `Host` header names on *this*
 * deployment. Reads `NEXT_PUBLIC_SITE_URL` (via `foundation/config/siteUrl`)
 * exactly once, so it never needs `NODE_ENV` to decide what "production"
 * means — see that module's comment for why that check is unsafe on staging
 * and on Vercel previews, which both build with `NODE_ENV=production`.
 */
export function getExamFromHost(host: string | null | undefined): string | null {
  return examFromHostAndSite(host, siteHostname(SITE_URL));
}
