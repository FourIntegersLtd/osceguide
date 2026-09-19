/**
 * Where the retiring client's URLs now point.
 *
 * `frontend/` is still serving these addresses and people have them
 * bookmarked, in emails and in the marketing site. ADR 0002 moved every
 * signed-in screen under `/app/<workspace>`, so each old path needs an answer
 * rather than a 404.
 *
 * Kept as data, in one file, with a test: a redirect table written inline in
 * middleware is where redirect loops come from, and this one has to be read
 * alongside the route tree when either changes.
 */

import { PERSONAL_SLUG } from "@/foundation/routing/workspace";

export interface LegacyRedirect {
  /** The retiring path, without a query string. */
  from: string;
  /** Where it goes now. `:slug` is filled from the matched old path. */
  to: string;
}

const personal = (path: string) => `/app/${PERSONAL_SLUG}${path}`;

/**
 * Exact consumer paths. The old client put these at the site root, which is
 * the habit ADR 0002 replaced.
 */
export const CONSUMER_REDIRECTS: readonly LegacyRedirect[] = [
  { from: "/dashboard", to: personal("/dashboard") },
  // The first cut of platform-web called the dashboard "practice". Both
  // spellings land in the same place so neither is a dead link.
  { from: "/practice", to: personal("/dashboard") },
  { from: "/mocks", to: personal("/mocks") },
  { from: "/stations", to: personal("/stations") },
  { from: "/library", to: personal("/library") },
  { from: "/slides", to: personal("/library") },
  { from: "/summary", to: personal("/library") },
  { from: "/community", to: personal("/discussion") },
  { from: "/discussion", to: personal("/discussion") },
  { from: "/marketplace", to: personal("/peers") },
  { from: "/peers", to: personal("/peers") },
  { from: "/human-practice", to: personal("/peers") },
  { from: "/transcripts", to: personal("/transcripts") },
  { from: "/debriefs", to: personal("/debriefs") },
  { from: "/feedbacks", to: personal("/feedbacks") },
  { from: "/achievements", to: personal("/achievements") },
  { from: "/settings", to: personal("/settings") },
  { from: "/messages", to: personal("/messages") },
  { from: "/access", to: personal("/access") },
  { from: "/welcome", to: personal("/welcome") },
  { from: "/auth/login", to: "/login" },
  { from: "/auth/register", to: "/register" },
  { from: "/auth/forgot-password", to: "/forgot-password" },
  { from: "/auth/reset-password", to: "/reset-password" },
];

/**
 * Prefix rewrites, applied in order, first match wins.
 *
 * `$1` is the remainder of the path after the matched prefix.
 */
export const PREFIX_REDIRECTS: readonly { pattern: RegExp; to: string }[] = [
  // The staff console. Checked before the generic org rule so that
  // `/b2b/platform` is never read as an organisation called "platform".
  { pattern: /^\/b2b\/platform(\/.*)?$/, to: "/staff$1" },
  // A rostered trainee, who is inside an organisation the token already names.
  { pattern: /^\/b2b\/trainee(\/.*)?$/, to: "/app$1" },
  // Partner and practice arms carried their own prefix; the workspace slug
  // that follows is enough now.
  { pattern: /^\/b2b\/partner\/([^/]+)(\/.*)?$/, to: "/app/$1$2" },
  { pattern: /^\/b2b\/practice\/([^/]+)(\/.*)?$/, to: "/app/$1$2" },
  // An institution workspace. `dashboard` was its landing screen.
  { pattern: /^\/b2b\/([^/]+)\/sessions(\/.*)?$/, to: "/app/$1/sessions$2" },
  { pattern: /^\/b2b\/([^/]+)(\/.*)?$/, to: "/app/$1$2" },
  // The first cut of platform-web, before ADR 0002.
  { pattern: /^\/assess\/trainee(\/.*)?$/, to: "/app$1" },
  { pattern: /^\/assess\/([^/]+)(\/.*)?$/, to: "/app/$1$2" },
  { pattern: /^\/hire\/([^/]+)(\/.*)?$/, to: "/app/$1$2" },
  { pattern: /^\/platform(\/.*)?$/, to: "/staff$1" },
  // Consumer sub-trees whose leaf varies.
  { pattern: /^\/mocks(\/.+)$/, to: `/app/${PERSONAL_SLUG}/mocks$1` },
  { pattern: /^\/summary(\/.+)$/, to: `/app/${PERSONAL_SLUG}/library$1` },
  { pattern: /^\/transcripts(\/.+)$/, to: `/app/${PERSONAL_SLUG}/transcripts$1` },
  { pattern: /^\/debriefs(\/.+)$/, to: `/app/${PERSONAL_SLUG}/debriefs$1` },
  { pattern: /^\/feedbacks(\/.+)$/, to: `/app/${PERSONAL_SLUG}/feedbacks$1` },
  { pattern: /^\/community\/(.+)$/, to: `/app/${PERSONAL_SLUG}/discussion/$1` },
];

const EXACT = new Map(CONSUMER_REDIRECTS.map((r) => [r.from, r.to]));

/**
 * The new address for a retiring path, or null if the path is already current.
 *
 * Never returns its own input, so a caller cannot build a redirect loop out of
 * it even if the table gains a bad row.
 */
export function legacyDestination(pathname: string): string | null {
  const trimmed = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;

  const exact = EXACT.get(trimmed);
  if (exact && exact !== trimmed) return exact;

  for (const { pattern, to } of PREFIX_REDIRECTS) {
    const match = trimmed.match(pattern);
    if (!match) continue;
    const destination = trimmed.replace(pattern, to).replace(/\/+$/, "") || "/";
    if (destination !== trimmed) return destination;
  }
  return null;
}
