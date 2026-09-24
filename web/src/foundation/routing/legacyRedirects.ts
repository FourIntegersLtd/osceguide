/**
 * Where the retiring client's URLs now point.
 *
 * `frontend/` is still serving these addresses and people have them
 * bookmarked, in emails and in the marketing site. ADR 0002 moved every
 * signed-in screen under `/app/<workspace>`, so each old path needs an answer
 * rather than a 404.
 *
 * Two rules about this table, both learned the hard way:
 *
 * 1. **Every destination must be a route that exists.** A redirect that lands
 *    on a 404 is worse than no redirect at all, because the address bar has
 *    changed and the reader assumes they mistyped it. Several words changed
 *    underneath these rules — a *session* became a **sitting**, a slot's
 *    *feedback* screen became the **review** screen, `[orgSlug]/templates`
 *    became the **station-templates** section of Authoring, a *feedback* became
 *    an **attempt** — and the table kept spelling the old word in the new URL.
 *    `legacyRedirects.test.ts` now checks destinations against the route tree
 *    instead of restating this file.
 * 2. **Specific before generic.** `PREFIX_REDIRECTS` is first-match-wins, so a
 *    rule that renames a sub-tree must sit above the rule that merely drops the
 *    arm prefix, or the generic one swallows it.
 *
 * Where a retiring screen has no counterpart, the rule points at the arm's
 * landing screen — `dashboard` is the one screen every arm declares — rather
 * than at a plausible-looking path that answers nothing.
 */

import { PERSONAL_SLUG } from "@/foundation/routing/workspace";

export interface LegacyRedirect {
  /** The retiring path, without a query string. */
  from: string;
  /** Where it goes now. `$1` is filled from the matched old path. */
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
  { from: "/library", to: personal("/summary") },
  { from: "/slides", to: personal("/slides") },
  { from: "/summary", to: personal("/summary") },
  { from: "/podcast", to: personal("/podcast") },
  { from: "/articles", to: personal("/articles") },
  { from: "/blogs", to: personal("/articles") },
  { from: "/community", to: personal("/discussion") },
  { from: "/discussion", to: personal("/discussion") },
  { from: "/marketplace", to: personal("/peers") },
  { from: "/peers", to: personal("/peers") },
  { from: "/partner-marketplace", to: personal("/peers") },
  { from: "/human-practice", to: personal("/peers") },
  { from: "/transcripts", to: personal("/transcripts") },
  /*
   * One debrief is still a page of its own; the *list* was never a page here —
   * `DebriefHistory` is a panel on the attempt it belongs to. So the list of
   * everything they have sat is where this lands, and it is the same list the
   * old screen showed.
   */
  { from: "/debriefs", to: personal("/transcripts") },
  /*
   * A *feedback* was the retiring backend's name for one marked attempt, and
   * the screen is `/attempts/<id>` now. The old address carries a document id
   * that is not an attempt id, so there is nothing to carry across: the list of
   * everything they have sat is both what `/feedbacks` showed and the only
   * honest destination for one row of it.
   */
  { from: "/feedbacks", to: personal("/transcripts") },
  { from: "/achievements", to: personal("/achievements") },
  { from: "/settings", to: personal("/settings") },
  { from: "/messages", to: personal("/messages") },
  // Billing lives under Settings, where the retiring client kept it. `/access`
  // was briefly a destination of its own rendering the same panel.
  { from: "/access", to: `${personal("/settings")}?tab=payments` },
  { from: "/settings/referrals", to: `${personal("/settings")}?tab=referrals` },
  /*
   * The welcome video went with the voice-onboarding flow that owned it, and
   * nothing replaces that yet — so the bookmark lands where a new person
   * actually starts rather than on a page that no longer exists.
   */
  { from: "/welcome", to: personal("/dashboard") },
  // Stripe's return addresses. The backend hardcodes these two against
  // platform-web, so an emailed receipt link from the old app still arrives.
  { from: "/payments/success", to: "/billing/complete" },
  { from: "/payments/cancel", to: "/pricing" },
  // Back-office addresses; there is one console now.
  { from: "/admin", to: "/staff" },
  { from: "/admin/general", to: "/staff" },
  { from: "/admin/partner-attribution", to: "/staff/growth" },
  { from: "/users", to: "/staff/users" },
  { from: "/comments", to: "/staff/moderation" },
  { from: "/auth/login", to: "/login" },
  { from: "/auth/register", to: "/register" },
  { from: "/auth/forgot-password", to: "/forgot-password" },
  { from: "/auth/reset-password", to: "/reset-password" },
];

/**
 * Prefix rewrites, applied in order, first match wins.
 *
 * `$1` is the first capture group of the matched pattern.
 */
export const PREFIX_REDIRECTS: readonly { pattern: RegExp; to: string }[] = [
  /*
   * The four console sign-ins. There is one sign-in now and the workspace a
   * person lands in comes from their memberships, so all of them are the same
   * page. They are listed first because the generic org rule below would
   * otherwise read "platform", "institution" or "partner" as a workspace slug
   * and send a signed-out visitor to a 404.
   */
  { pattern: /^\/b2b\/(?:platform|institution|partner|trainee)\/login$/, to: "/login" },
  { pattern: /^\/b2b\/login$/, to: "/login" },
  { pattern: /^\/b2b\/practice\/[^/]+\/login$/, to: "/login" },
  /*
   * Spelled without the `(auth)` route group: a group is invisible in the
   * URL, so the address the retiring client actually served is
   * `/b2b/change-password`. The rule that matched the literal group name
   * never fired, and the generic org rule below read "change-password" as a
   * workspace and sent the visitor to a 404.
   */
  { pattern: /^\/b2b\/change-password$/, to: "/change-password" },
  { pattern: /^\/b2b\/select-workspace$/, to: "/app" },
  // A marketing page, not a workspace.
  { pattern: /^\/b2b\/institutions$/, to: "/institutions" },
  { pattern: /^\/b2b(?:\/(?:partner|practice))?$/, to: "/login" },

  // The staff console. Checked before the generic org rule so that
  // `/b2b/platform` is never read as an organisation called "platform".
  { pattern: /^\/b2b\/platform(\/.*)?$/, to: "/staff$1" },

  /*
   * A rostered trainee is inside an organisation the token already names, so
   * the arm prefix and the `trainee` segment both fall away — and what is left
   * is the personal workspace's `trainee` screens. `/app/practice` would read
   * "practice" as a workspace slug, which is what the old rule here did.
   */
  { pattern: /^\/b2b\/trainee\/sessions\/([^/]+)\/result$/, to: personal("/trainee/results/$1") },
  { pattern: /^\/b2b\/trainee\/sessions\/([^/]+)$/, to: personal("/trainee/sittings/$1") },
  /*
   * An emailed join link named a *slot*, and this platform opens a candidate's
   * room by sitting, so the id cannot become a path of its own. It rides along
   * as a query and the trainee's screen resolves it against the sittings it has
   * already loaded — which is also why a link for somebody else resolves to
   * nothing rather than to a plausible room.
   */
  { pattern: /^\/b2b\/trainee\/join\/([^/]+)$/, to: personal("/trainee?slot=$1") },
  { pattern: /^\/b2b\/trainee\/(?:sessions|circuit-feedback|join)(\/.*)?$/, to: personal("/trainee") },
  { pattern: /^\/b2b\/trainee\/transcript$/, to: personal("/transcripts") },
  { pattern: /^\/b2b\/trainee(?:\/(.*))?$/, to: personal("/trainee/$1") },

  /*
   * An institution's examination tree. A *session* is a **sitting** now, a
   * circuit's console is addressed by the circuit alone, and the run screen's
   * per-slot *feedback* page is the review screen — so the sub-paths cannot be
   * carried across verbatim, and are renamed above the rule that drops the arm
   * prefix.
   */
  {
    pattern: /^\/b2b\/([^/]+)\/sessions\/[^/]+\/circuits\/[^/]+\/run\/slots\/([^/]+)(\/feedback)?$/,
    to: "/app/$1/slots/$2/review",
  },
  { pattern: /^\/b2b\/([^/]+)\/sessions\/([^/]+)\/circuits\/new$/, to: "/app/$1/sittings/$2/circuits/new" },
  { pattern: /^\/b2b\/([^/]+)\/sessions\/([^/]+)\/circuits\/([^/]+)(\/.*)?$/, to: "/app/$1/circuits/$3" },
  { pattern: /^\/b2b\/([^/]+)\/sessions\/([^/]+)\/candidates\/[^/]+(?:\/.*)?$/, to: "/app/$1/sittings/$2/results" },
  { pattern: /^\/b2b\/([^/]+)\/sessions\/([^/]+)\/edit$/, to: "/app/$1/sittings/$2" },
  { pattern: /^\/b2b\/([^/]+)\/sessions(\/.*)?$/, to: "/app/$1/sittings$2" },
  // Org-level results were a list of exam sittings; there is no separate screen.
  { pattern: /^\/b2b\/([^/]+)\/results$/, to: "/app/$1/sittings" },

  /*
   * Content sat on `[orgSlug]/stations` and `[orgSlug]/templates`; both are
   * sections of one Authoring screen now, and the feedback-template builder
   * merged into rubric versions.
   */
  { pattern: /^\/b2b\/([^/]+)\/stations\/templates(\/new)?$/, to: "/app/$1/authoring/station-templates$2" },
  { pattern: /^\/b2b\/([^/]+)\/stations\/feedback-templates(?:\/.*)?$/, to: "/app/$1/authoring/rubrics" },
  { pattern: /^\/b2b\/([^/]+)\/stations(?:\/.*)?$/, to: "/app/$1/authoring/stations" },
  { pattern: /^\/b2b\/([^/]+)\/templates(\/new)?$/, to: "/app/$1/authoring/station-templates$2" },
  // The team hub's sub-screens are tabs of one screen now.
  { pattern: /^\/b2b\/([^/]+)\/team(?:\/.*)?$/, to: "/app/$1/team" },

  // A partner's catalogue is the same Authoring sections, scoped to their org.
  { pattern: /^\/b2b\/partner\/([^/]+)\/exams(?:\/.*)?$/, to: "/app/$1/authoring/exams" },
  { pattern: /^\/b2b\/partner\/([^/]+)\/templates(?:\/.*)?$/, to: "/app/$1/authoring/station-templates" },
  { pattern: /^\/b2b\/partner\/([^/]+)\/stations(?:\/.*)?$/, to: "/app/$1/authoring/stations" },
  { pattern: /^\/b2b\/partner\/([^/]+)\/users(?:\/.*)?$/, to: "/app/$1/team" },
  { pattern: /^\/b2b\/partner\/([^/]+)(\/.*)?$/, to: "/app/$1$2" },
  /*
   * A practice account sat exams through the same mock screens an institution
   * now mounts. Exams, a mock, and history all open that list; anything else
   * under the account still starts at the dashboard.
   */
  { pattern: /^\/b2b\/practice\/([^/]+)\/mocks(\/.*)?$/, to: "/app/$1/mocks$2" },
  { pattern: /^\/b2b\/practice\/([^/]+)\/(?:exams|history)(?:\/.*)?$/, to: "/app/$1/mocks" },
  { pattern: /^\/b2b\/practice\/([^/]+)(\/.*)?$/, to: "/app/$1/dashboard" },
  // An institution workspace's remaining screens are named the same thing.
  { pattern: /^\/b2b\/([^/]+)(\/.*)?$/, to: "/app/$1$2" },

  // The first cut of platform-web, before ADR 0002.
  { pattern: /^\/assess\/trainee(?:\/.*)?$/, to: personal("/trainee") },
  { pattern: /^\/assess\/([^/]+)(\/.*)?$/, to: "/app/$1$2" },
  { pattern: /^\/hire\/([^/]+)(\/.*)?$/, to: "/app/$1$2" },
  { pattern: /^\/platform(\/.*)?$/, to: "/staff$1" },

  /*
   * Consumer sub-trees whose leaf varies. Ordered specific-first for the same
   * reason as the console above: `/mocks/list` and `/mocks/customise` are not
   * set ids, and `/mocks/<id>/update` has no edit screen to go to.
   */
  { pattern: /^\/mocks\/(?:list|customise)$/, to: personal("/mocks") },
  { pattern: /^\/mocks\/([^/]+)\/update$/, to: personal("/mocks/$1") },
  { pattern: /^\/mocks(\/.+)$/, to: personal("/mocks$1") },
  { pattern: /^\/summary(\/.+)$/, to: personal("/summary") },
  { pattern: /^\/blogs(\/.+)$/, to: personal("/articles") },
  { pattern: /^\/transcripts(\/.+)$/, to: personal("/transcripts$1") },
  { pattern: /^\/debriefs(\/.+)$/, to: personal("/debriefs$1") },
  { pattern: /^\/feedbacks(\/.+)?$/, to: personal("/transcripts") },
  // The feed opens one thread off a query, so a question id survives the move.
  { pattern: /^\/community\/question\/([^/]+)$/, to: `${personal("/discussion")}?question=$1` },
  { pattern: /^\/community(?:\/.*)?$/, to: personal("/discussion") },
  { pattern: /^\/human-practice(?:\/.*)?$/, to: personal("/peers") },
  { pattern: /^\/practice(?:\/.*)?$/, to: personal("/dashboard") },
  { pattern: /^\/settings\/referrals(?:\/.*)?$/, to: `${personal("/settings")}?tab=referrals` },
  { pattern: /^\/settings(?:\/.*)?$/, to: personal("/settings") },
  { pattern: /^\/payments\/success$/, to: "/billing/complete" },
  { pattern: /^\/payments(?:\/.*)?$/, to: "/pricing" },
  { pattern: /^\/admin(?:\/.*)?$/, to: "/staff" },
  { pattern: /^\/users(?:\/.*)?$/, to: "/staff/users" },
  { pattern: /^\/comments(?:\/.*)?$/, to: "/staff/moderation" },
  // Feature requests were superseded by the landing's own sections.
  { pattern: /^\/features(?:\/.*)?$/, to: "/" },
  { pattern: /^\/partner\/([^/]+)\/reporting$/, to: "/app/$1/reporting" },
  { pattern: /^\/partner(?:\/.*)?$/, to: "/institutions" },
  /*
   * `/app/<workspace>/access` was a destination of platform-web's own for a
   * few weeks, rendering the Settings panel that shows what somebody has
   * bought. It is a Settings tab now.
   *
   * Listed here as well as in the exact table because the exact one only
   * covers the retiring client's root-level `/access`; anybody who bookmarked
   * a workspace URL in the meantime would have got a 404, which is what
   * driving the real app turned up.
   */
  { pattern: /^\/app\/([^/]+)\/access$/, to: "/app/$1/settings?tab=payments" },
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
