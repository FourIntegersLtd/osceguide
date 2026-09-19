import type { SetEntry, StationSet } from "@/domains/train/api";

/**
 * The arithmetic the mocks screens do, kept out of the components.
 *
 * The retiring client read most of this off the mock document — `duration`,
 * `completed`, `attempted`, `has_feedback` were all columns the old backend
 * wrote at create time and then had to keep true. `platform-api` stores the
 * facts instead (how many entries, how many were attempted, when the set was
 * finished) and leaves the reading to whoever is looking, which is why this is
 * a file of pure functions rather than fields.
 */

/** Two positive integers is all a station's clock is: reading, then talking. */
export interface StationTimings {
  readingSeconds: number;
  simulationSeconds: number;
}

/**
 * How long a session takes, in whole minutes.
 *
 * The old card printed a stored `duration`. Deriving it from the exam's own
 * timings means a session created before an exam's clock changed no longer
 * advertises the old length.
 */
export function sessionMinutes(stationCount: number, timings: StationTimings | null): number {
  if (!timings) return 0;
  const perStation = timings.readingSeconds + timings.simulationSeconds;
  return Math.round((stationCount * perStation) / 60);
}

export function entriesInOrder(set: StationSet): SetEntry[] {
  return (set.entries ?? []).slice().sort((a, b) => a.position - b.position);
}

export type SessionState = "locked" | "completed" | "attempted" | "new";

export function sessionState(set: StationSet): SessionState {
  if (set.locked) return "locked";
  if (set.completed_at !== null) return "completed";
  return set.attempted_entries > 0 ? "attempted" : "new";
}

/**
 * "Start" or "Review".
 *
 * Locked sets are review-only. Otherwise finishing the set is what turns the
 * card over — the old client branched on `has_feedback`, a field this backend
 * does not carry, and an attempted-but-unfinished set read as "Start" there
 * too, so the visible behaviour is unchanged for everything but a set whose
 * marking is still running.
 */
export function sessionAction(set: StationSet): "Start" | "Review" {
  const state = sessionState(set);
  return state === "locked" || state === "completed" ? "Review" : "Start";
}

/**
 * Current subscription first, lapsed ones behind a second heading.
 *
 * A lapsed entitlement locks a set rather than deleting it, so the work comes
 * back on renewal; grouping is what stops a year of locked sets burying the
 * three somebody can actually sit.
 */
export function groupSets(sets: readonly StationSet[]): {
  currentSubscription: StationSet[];
  inactiveSubscriptions: StationSet[];
} {
  const currentSubscription: StationSet[] = [];
  const inactiveSubscriptions: StationSet[] = [];
  for (const set of sets) {
    (set.locked ? inactiveSubscriptions : currentSubscription).push(set);
  }
  return { currentSubscription, inactiveSubscriptions };
}

/** Every station version this person has already had a go at, in any set. */
export function attemptedVersionIds(sets: readonly StationSet[]): Set<string> {
  const ids = new Set<string>();
  for (const set of sets) {
    for (const entry of set.entries ?? []) {
      if (entry.attempts > 0) ids.add(entry.station_version_id);
    }
  }
  return ids;
}

/**
 * Stations that were started and not finished, for the Combine tab.
 *
 * The old backend answered this with `/api/attempted_incomplete_stations`.
 * The set list carries every entry with its attempt count, so the same
 * question is a filter here rather than a round trip — and it stays correct
 * when a set is locked mid-way, which the endpoint did not.
 */
export function incompleteVersionIds(
  sets: readonly StationSet[],
  attemptLimit: number,
): string[] {
  const ids = new Set<string>();
  for (const set of sets) {
    for (const entry of set.entries ?? []) {
      if (entry.attempts > 0 && entry.attempts < attemptLimit) {
        ids.add(entry.station_version_id);
      }
    }
  }
  return [...ids];
}

/**
 * Choose the stations for a session of `count`.
 *
 * `POST /me/station-sets` takes explicit version ids; the retiring backend's
 * `customise_mock` took a number and picked for you. Picking here keeps the
 * form the candidate knows — "how many stations?" — without inventing a
 * server-side chooser, and prefers stations they have not seen so a new
 * session is new work by default.
 */
export function chooseStations<T extends { version_id: string }>(
  available: readonly T[],
  count: number,
  options: { excludeVersionIds?: ReadonlySet<string> } = {},
): T[] {
  const exclude = options.excludeVersionIds ?? new Set<string>();
  const fresh = available.filter((station) => !exclude.has(station.version_id));
  const pool = fresh.length >= count ? fresh : available;
  return shuffle(pool).slice(0, Math.max(0, count));
}

function shuffle<T>(items: readonly T[]): T[] {
  const copy = items.slice();
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    const a = copy[i] as T;
    const b = copy[j] as T;
    copy[i] = b;
    copy[j] = a;
  }
  return copy;
}

export interface Milestone {
  reached: boolean;
  milestone?: number;
  stationBadges: number;
}

/** One badge every five stations, the same ladder the old client celebrated. */
export function checkMilestone(currentCount: number, previousCount: number): Milestone {
  const milestones = Array.from({ length: Math.ceil(currentCount / 5) }, (_, i) => (i + 1) * 5);
  const crossed = milestones.find(
    (milestone) => previousCount < milestone && currentCount >= milestone,
  );
  return {
    reached: crossed !== undefined,
    milestone: crossed,
    stationBadges: Math.floor(currentCount / 5),
  };
}
