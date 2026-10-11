/**
 * The addresses that need a session.
 *
 * Two things assert this and they must not disagree: `RequireSession` refuses
 * them to a browser, and `app/robots.ts` refuses them to a crawler. Keeping the
 * list in the route tier rather than in the metadata file is what stops them
 * drifting — a `/staff` that is disallow-listed but not guarded is a console
 * that quietly advertises its own URLs, and the reverse is a page a search
 * engine indexes by accident.
 *
 * Listed as prefixes because that is what the standard asks for; a trailing
 * slash means "this sub-tree", no slash means "this one address".
 */
export const PRIVATE_PATH_PREFIXES: readonly string[] = [
  "/app/",
  "/staff/",
  "/billing/",
  "/api/",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/accept-invitation",
  "/change-password",
];

/**
 * The public marketing surface, in the order it is worth crawling.
 *
 * Hand-written rather than derived from the route tree on purpose: `frontend/`
 * generated this by crawling and duly published `/admin/sca/stations/create/
 * auto-station` and `/b2b/platform/organizations`, because a crawler cannot
 * tell a landing page from a console. The cost is that a new marketing page has
 * to be added here as well as built.
 *
 * No CASC landing exists — `app/(public)/exams/[exam]` answers these five and
 * `notFound()` for anything else — so an entry for one would be a 404 that
 * spends crawl budget and then reports a failure.
 */
export const PUBLIC_MARKETING_PATHS: readonly string[] = [
  "",
  "/institutions",
  "/pricing",
  "/blogs",
  "/exams/avodeck",
  "/exams/classic",
  "/exams/ortho",
  "/exams/plab",
  "/exams/sca",
  "/compliances/terms-of-service",
  "/compliances/privacy-policy",
  "/compliances/cookies-policy",
  "/compliances/legal-disclaimer",
  "/compliances/referrals",
  "/compliances/accessibility",
];
