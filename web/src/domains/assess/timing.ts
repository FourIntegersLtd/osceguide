/**
 * Circuit clock rules the form needs to agree with the server about.
 *
 * `platform-api` clamps every timing value in `sittings/domain.py`
 * (`normalise_timing`), so nothing here is authoritative — a browser that sent
 * a break after the last station would simply have it dropped. The rules are
 * mirrored for one reason: so the form cannot offer a control whose answer the
 * server is going to throw away, which reads as the save being ignored.
 *
 * Two deliberate divergences from the retiring client:
 *
 * - A break has **one** length for the whole circuit (`break_minutes`), not a
 *   length per break. `b2b` carried `B2BExamBreakRule.minutes` on every entry;
 *   the platform's `Timing` has a single `break_minutes`, and inventing a
 *   per-break duration here would be a field nothing reads.
 * - Breaks exist in **exam mode only**. `normalise_timing` builds none for any
 *   other mode, because a training circuit rotates one group through stations
 *   and never stops between them.
 */

/** `domain.DEFAULT_BREAK_MINUTES`. */
export const DEFAULT_BREAK_MINUTES = 5;

/** `domain.DEFAULT_READING_MINUTES` and `READING_BOUNDS`. */
export const DEFAULT_READING_MINUTES = 3;
export const READING_MINUTES_BOUNDS = { min: 1, max: 30 } as const;

/** Clamp reading time into what the server will keep, defaulting when unusable. */
export function clampReadingMinutes(minutes: number): number {
  if (!Number.isFinite(minutes)) return DEFAULT_READING_MINUTES;
  return Math.min(
    READING_MINUTES_BOUNDS.max,
    Math.max(READING_MINUTES_BOUNDS.min, Math.round(minutes)),
  );
}

/** `domain.DEFAULT_SIMULATION_MINUTES`. */
export const DEFAULT_SIMULATION_MINUTES = 10;

/** `domain.BREAK_BOUNDS`. */
export const BREAK_MINUTES_BOUNDS = { min: 1, max: 60 } as const;

/** `domain.EXAM_MAX_STATIONS`. */
export const MAX_EXAM_STATIONS = 12;

/** `domain.plan_slots`: an exam circuit is one candidate's sitting. */
export const MAX_EXAM_CANDIDATES = 1;

/** The bulk route makes one circuit per candidate, up to `CreateExamCircuits.candidate_user_ids`. */
export const MAX_BULK_CANDIDATES = 200;

/**
 * The station numbers a break may follow: 1-based, and never the last one.
 *
 * A break sits *between* two stations, so with one station there is nowhere for
 * it to go and with three it can only follow the first or the second.
 */
export function breakPositions(stationCount: number): number[] {
  return Array.from({ length: Math.max(stationCount - 1, 0) }, (_, index) => index + 1);
}

/**
 * Keep only the breaks that still fit, de-duplicated and ascending.
 *
 * The retiring client's `clampExamBreaksForStationCount` did the same job while
 * also carrying each break's minutes; this drops the selections that stopped
 * being legal when a station came off the circuit — the case a form somebody
 * edits twice actually hits.
 */
export function clampBreaks(breaks: readonly number[], stationCount: number): number[] {
  if (stationCount <= 1) return [];
  const highest = stationCount - 1;
  const kept = new Set<number>();
  for (const after of breaks) {
    if (!Number.isInteger(after) || after < 1 || after > highest) continue;
    kept.add(after);
  }
  return [...kept].sort((a, b) => a - b);
}

/** Clamp a break length into what the server will accept, defaulting when unusable. */
export function clampBreakMinutes(minutes: number): number {
  if (!Number.isFinite(minutes)) return DEFAULT_BREAK_MINUTES;
  return Math.min(
    BREAK_MINUTES_BOUNDS.max,
    Math.max(BREAK_MINUTES_BOUNDS.min, Math.round(minutes)),
  );
}

/** Whether this circuit's mode is the one that has breaks at all. */
export function modeSupportsBreaks(mode: string): boolean {
  return mode.trim().toLowerCase() === "exam";
}
