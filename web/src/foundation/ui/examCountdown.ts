import { dayFromIso, daysBetween } from "@/foundation/ui/dateDay";

/**
 * The exam-date countdown, one copy for the dashboard and the shell. Only the day is stored
 * (`exam_date`, `YYYY-MM-DD`) and it is read as a local day, the same day the calendar shows, so
 * the count does not move with the hour or the time zone.
 */

/** Whole calendar days from today to the exam day (negative once it has passed), or `null` with no date. */
export function daysUntil(examDate: string | null | undefined, now: number): number | null {
  const target = dayFromIso(examDate);
  return target ? daysBetween(new Date(now), target) : null;
}

/**
 * "4 weeks to go", "5 days to go", "Exam day", the passed message, or `undefined` when there is
 * no date.
 */
export function examCountdown(
  examDate: string | null | undefined,
  now: number = Date.now(),
): string | undefined {
  const days = daysUntil(examDate, now);
  if (days === null) return undefined;
  if (days < 0) return "Exam date has passed";
  if (days === 0) return "Exam day";
  if (days >= 7) {
    const weeks = Math.ceil(days / 7);
    return `${weeks} week${weeks === 1 ? "" : "s"} to go`;
  }
  return `${days} day${days === 1 ? "" : "s"} to go`;
}
