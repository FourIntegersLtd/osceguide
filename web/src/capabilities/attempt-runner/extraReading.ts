"use client";

import { useSession } from "@/foundation/session";

/**
 * A person's own extra reading time, as a percentage.
 *
 * An access arrangement carried on `/me` (`users.extra_reading_percent`). It
 * extends the reading period of their *own practice* and never a circuit's
 * clock: a circuit runs one clock for everybody on it, so stretching it for one
 * candidate would stretch it for the rest. An institution granting extra time in
 * an examination hall does it to the circuit's own timing instead. See
 * `docs/port-gaps.md` and platform-api's S-2.
 */
export function useExtraReadingPercent(): number {
  const { session } = useSession();
  const percent = session?.user.extra_reading_percent ?? 0;
  return percent > 0 ? percent : 0;
}

/**
 * Extend a reading period by a percentage, rounded to whole seconds.
 *
 * Zero — the default, and everybody with no arrangement — returns the base
 * unchanged, so an unaccommodated attempt is timed exactly as the exam defines
 * it. Only the reading phase is extended; the consultation is not.
 */
export function withExtraReadingTime(baseSeconds: number, percent: number): number {
  if (baseSeconds <= 0 || percent <= 0) return baseSeconds;
  return Math.round(baseSeconds * (1 + percent / 100));
}
