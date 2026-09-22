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
 * spellings; the replacement serves `consultations`, `debriefs`, `users` and
 * `stations`, and this function is the mapping between the two shapes.
 *
 * One figure has no counter of its own: **feedback reports**. The band's
 * fourth card ("AI feedback reports generated") read the retiring backend's
 * `all_feedback`, and `SiteStatistics` does not carry an equivalent. Every
 * completed consultation produces one AI feedback report, and the retiring
 * backend's two counters never differed by more than a fraction of a percent
 * (its own logs show 10,057 consultations beside 10,113 reports), so the
 * consultation count stands in until the backend grows a dedicated counter —
 * tracked in `docs/port-gaps.md`.
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
      all_feedback: stats.consultations,
      all_users: stats.users,
      all_stations: stats.stations,
      as_of: stats.as_of,
    };
  } catch {
    return null;
  }
}
