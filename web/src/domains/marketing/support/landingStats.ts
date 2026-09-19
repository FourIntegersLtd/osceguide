
/**
 * The counters the hero and the numbers band show.
 *
 * The retiring backend served these from `/api/landing`. `platform-api` has no
 * equivalent yet, so this returns `null` and both callers already degrade to
 * hiding their figures — which is the right behaviour for a marketing number
 * nobody can verify, and better than showing a zero.
 *
 * When the backend grows the route, this is the one place to point at it.
 */
/**
 * The figures the landing page's numbers band shows.
 *
 * Every field is optional because **platform-api does not serve this yet**.
 * The retiring backend had `/landing`; the replacement has no public
 * statistics endpoint, so `fetchLandingStats` returns null today and the band
 * hides itself rather than showing zeroes. Tracked in `docs/port-gaps.md`.
 */
export interface LandingStats {
  all_consultations?: number;
  all_debriefs?: number;
  all_feedback?: number;
  all_users?: number;
  all_stations?: number;
}

/**
 * The figures, when there are any.
 *
 * `platform-api` has no public statistics endpoint. The retiring backend
 * served `/landing`; asking the replacement for it 404s on every view of the
 * busiest public page, so this does not ask. The band hides itself on `null`,
 * which is the same thing a failed request produced, and the page is one
 * request lighter until the endpoint exists.
 *
 * Putting it back is this function's body. See `docs/port-gaps.md`.
 */
export async function fetchLandingStats(): Promise<LandingStats | null> {
  return null;
}
