import type { SetEntry, StationSet } from "@/domains/train/api";
import type { AttemptHistoryItem } from "@/capabilities/attempt-runner";
import { isOrgSurface, type Surface } from "@/capabilities/surface";
import { ORG_NO_ACCESS, describeRefusal } from "@/capabilities/stations/refusal";
import { plural } from "@/foundation/format";

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
 * Locked sets are review-only. Otherwise feedback is what turns the card
 * over, as in the old client: `feedback_ready` is true once any station in the
 * set has been marked. Attempted without feedback still reads "Start".
 */
export function sessionAction(set: StationSet): "Start" | "Review" {
  return set.locked || set.feedback_ready ? "Review" : "Start";
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

/**
 * Only the fields the feedback-status decision actually looks at.
 *
 * A narrower type than `AttemptHistoryItem` so the pure function below can be
 * tested with plain literals instead of a full API row.
 */
export type AttemptStatusRecord = Pick<AttemptHistoryItem, "status" | "has_result" | "created_at">;

/**
 * What a session's end screen and a station row show for one entry's marking.
 *
 * - `review`: a result exists, so there is feedback to open.
 * - `marking`: the consultation finished and is waiting on its result. This is
 *   the only state that will ever resolve on its own — everything else is a
 *   dead end and the screen should say so plainly instead of spinning forever.
 * - `failed`: the attempt's own status is `failed` (the worker gave up, or the
 *   candidate abandoned mid-consultation). Nothing will mark it.
 * - `not_attempted`: no relevant attempt, or the most recent one never got
 *   past `created`/`running` — the candidate opened the station and left
 *   before finishing it, so there is nothing to mark yet.
 * - "unread": the attempts could not be read, which says nothing about the feedback.
 */
export type StationFeedbackState = "review" | "marking" | "failed" | "not_attempted" | "unread";

/** The one attempt, among several against the same entry, worth reading a state off. */
function mostRecentAttempt<T extends { created_at: string }>(
  attempts: readonly T[],
): T | null {
  if (attempts.length === 0) return null;
  return attempts.reduce((latest, candidate) =>
    candidate.created_at > latest.created_at ? candidate : latest,
  );
}

/**
 * Decide one entry's feedback state from its most recent attempt's real
 * `status`, not from "an attempt with no result exists".
 *
 * The bug this replaces: `sat.length > 0 && !marked` called every attempt
 * without a result "being marked", including one still `created` (never
 * started) or `failed` — both of which nothing will ever mark, so the
 * screen showed a spinner that never stopped.
 */
export function stationFeedbackState(
  attempts: readonly AttemptStatusRecord[],
): StationFeedbackState {
  const latestAttempt = mostRecentAttempt(attempts);
  if (!latestAttempt) return "not_attempted";
  // The newest consultation is finished and its result is on its way.
  if (latestAttempt.status === "interaction_complete" && !latestAttempt.has_result) return "marking";
  // Any earlier result stays reachable: opening the station again, or a later
  // failed run, must not hide feedback the candidate already has.
  if (attempts.some((attempt) => attempt.has_result)) return "review";
  if (latestAttempt.status === "failed") return "failed";
  // `created` or `running`: the candidate opened the station but never
  // finished the consultation, so nothing is waiting to be marked.
  return "not_attempted";
}

/** Whether any entry is still genuinely being marked, and so worth polling for. */
export function anyStationMarking(states: readonly StationFeedbackState[]): boolean {
  return states.some((state) => state === "marking");
}

/**
 * Statuses at which a recording actually exists to look at.
 *
 * A transcript is written once the consultation's interaction is over, so an
 * attempt still `created` or `running` never produced one — even though it is
 * a row in the same attempts list. Mirrors `REVIEWABLE` in the backend's
 * `attempts/domain.py`.
 */
const STATUSES_WITH_TRANSCRIPT: ReadonlySet<string> = new Set([
  "interaction_complete",
  "evaluated",
  "failed",
]);

/**
 * Of a station's attempts, only the ones that actually left a transcript.
 *
 * The bug this replaces: a station's history row counted every attempt
 * against it as a transcript, including one the candidate opened and walked
 * away from without ever starting the consultation.
 */
export function attemptsWithTranscript<T extends { status: string }>(
  attempts: readonly T[],
): T[] {
  return attempts.filter((attempt) => STATUSES_WITH_TRANSCRIPT.has(attempt.status));
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

/** Where a flagged station reopens: inside the session it was flagged in. */
export function flaggedEntryPath(flag: { set_id: string; entry_id: string }): string {
  return `/mocks/${encodeURIComponent(flag.set_id)}/stations/${encodeURIComponent(flag.entry_id)}`;
}

export interface TrialLimits {
  stations: number;
  days: number;
  attempts_per_station: number;
}

/** The free trial's limits in words, as the server states them. */
function describeTrial(trial: TrialLimits): string {
  return `It covers ${trial.stations} stations, each sat up to ${trial.attempts_per_station} times, within ${trial.days} days of signing up.`;
}

/**
 * Why a new session cannot be built because the exam shows no stations, in words. The limits are the server's,
 * never numbers written here.
 */
export function nothingPickableMessage(input: {
  hasPaid: boolean | undefined;
  subscriptionExpired: boolean;
  trial: TrialLimits;
  /** Where the trainee is: an institution's or employer's gets no trial, no subscribing. */
  surface?: Surface;
}): string {
  if (input.surface && isOrgSurface(input.surface) && (input.subscriptionExpired || input.hasPaid === false)) return ORG_NO_ACCESS;
  if (input.subscriptionExpired) {
    return "Your access to this exam has ended, so there is nothing new to practise. Subscribe or ask your organisation to renew it.";
  }
  if (input.hasPaid === false) {
    return `Your free trial is used up. ${describeTrial(input.trial)} Subscribe to keep practising.`;
  }
  return "There are no stations for this exam yet.";
}

/**
 * What to tell somebody whose new session was refused, by the code the API answered with.
 * Access and unpublished stations read the same as when starting a station.
 */
export function describeCreateSetFailure(cause: unknown, surface?: Surface): string {
  return describeRefusal(cause, "We could not create this session. Please try again.", surface);
}

/** What a learner needs before a session: nothing to buy, nothing that sounds like a lab. */
export const BEFORE_YOU_START: readonly string[] = [
  "The built-in microphone on your laptop or phone is fine",
  "Headphones are optional. They cut down echo",
  "Find somewhere you can talk without interruptions, with a stable connection",
];

/**
 * The instruction page's rules. Rules 1 and 3 are the setup screen's BEFORE_YOU_START, so the two
 * pages never drift. The clock is the station runner's: reading time first, then the
 * consultation from Start simulation or the end of reading time, never from Start session.
 */
export function mockRules(attemptLimit: number): string[] {
  const attempts = attemptLimit === 1 ? "once" : `up to ${attemptLimit} times`;
  return [
    `You talk to an AI patient out loud. ${BEFORE_YOU_START[0]}. ${BEFORE_YOU_START[1]}.`,
    "Each station follows the same format. About halfway through, a prompt tells you to move from history taking to management.",
    `${BEFORE_YOU_START[2]}. If something goes wrong, flag the station and message support.`,
    `You can attempt each station ${attempts}. Each station opens with reading time, and the consultation starts when you press Start simulation or reading time runs out.`,
  ];
}

/** The most stations a new session may hold: the free stations left on the trial, else all of them. */
export function pickerMax(available: number, freeStationsLeft: number | null): number {
  return freeStationsLeft === null ? available : Math.min(available, freeStationsLeft);
}

/** The setup hint for a trial learner; null when access is paid for. */
export function trialStationsHint(freeStationsLeft: number | null, surface?: Surface): string | null {
  if ((surface && isOrgSurface(surface)) || freeStationsLeft === null) return null;
  if (freeStationsLeft === 0) return "Your free trial has no stations left.";
  return `Your free trial has ${plural(freeStationsLeft, "station")} left.`;
}

/**
 * What a station in a session is called. The server sends a title only once the station has been
 * sat (a name gives the case away), so before then it is its place in the session.
 */
export function stationLabel(entry: Pick<SetEntry, "station_title">, index: number): string {
  return entry.station_title ?? `Station ${index + 1}`;
}

export function sessionUpdatedMessage(stationCount: number): string {
  return `Session updated: ${plural(stationCount, "station")}`;
}

/** The line under the Combine tab's title: what it is for, or what unlocks it. */
export function combineIntro(hasSatStations: boolean): string {
  return hasSatStations
    ? "Pick the stations you found hardest and sit them again as one session."
    : "Available once you have sat a few stations. Then you can pick the ones you found hardest and sit them again as one session.";
}
