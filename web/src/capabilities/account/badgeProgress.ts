export const STATIONS_PER_BADGE = 5;
/** The station badge row always shows this many milestones, earned or not. */
const MIN_MILESTONES = 8;

/** Where a station count sits on the badge ladder: one badge every five stations. */
export function badgeProgress(stationCount: number): { earned: number; toNext: number; milestones: number[] } {
  const earned = Math.floor(stationCount / STATIONS_PER_BADGE);
  return {
    earned,
    toNext: STATIONS_PER_BADGE - (stationCount % STATIONS_PER_BADGE),
    milestones: Array.from(
      { length: Math.max(MIN_MILESTONES, earned + 1) },
      (_, index) => (index + 1) * STATIONS_PER_BADGE,
    ),
  };
}
