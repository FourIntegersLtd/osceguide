import { reportError } from "@/foundation/observability";
import { readSiteStatistics } from "@/domains/marketing/api";

/**
 * The figures the landing page's numbers band shows.
 *
 * Every field is optional: a partial answer still renders the band, and the
 * callers fall back to zero per figure rather than hiding everything.
 */
export interface LandingStats {
  all_consultations?: number;
  all_debriefs?: number;
  all_feedback?: number;
  all_users?: number;
  all_stations?: number;
  /** When the backend counted these — it caches the figures for ten minutes. */
  as_of?: string;
}

/**
 * The figures, from `GET /site/statistics`.
 *
 * The retiring backend served these from `/api/landing` with the `all_*`
 * spellings; the replacement serves `consultations`, `debriefs`, `feedback`,
 * `users` and `stations`, and this function is the mapping between the two
 * shapes. The feedback counter counts evaluated attempts — the dedicated
 * stand-in for the retiring `all_feedback` is gone.
 *
 * A failure returns `null` and both callers hide their figures, which is what
 * a failed request produced before: an unverifiable marketing number is worse
 * than no number.
 */
export async function fetchLandingStats(): Promise<LandingStats | null> {
  try {
    const stats = await readSiteStatistics();
    return {
      all_consultations: stats.consultations,
      all_debriefs: stats.debriefs,
      all_feedback: stats.feedback,
      all_users: stats.users,
      all_stations: stats.stations,
      as_of: stats.as_of,
    };
  } catch (cause) {
    // Hidden from the visitor on purpose, but never silent for us.
    reportError(cause);
    return null;
  }
}
