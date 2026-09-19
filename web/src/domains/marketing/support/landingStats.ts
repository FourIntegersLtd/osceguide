import { platformRequest } from "@/foundation/platform-client";

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

export async function fetchLandingStats(): Promise<LandingStats | null> {
  try {
    return await platformRequest<LandingStats>("/api/v1/landing");
  } catch {
    return null;
  }
}
