import { dayFromIso } from "@/foundation/ui/dateDay";

/**
 * The dashboard's exam-date countdown. Only the day is stored (`exam_date`,
 * `YYYY-MM-DD`) and it is read as a local day, the same day the calendar
 * shows, so the count does not move with the hour or the time zone.
 */

const MS_PER_DAY = 24 * 60 * 60 * 1000;

/** Whole calendar days from today to the exam day (negative once it has passed), or `null` with no date. */
function daysUntil(examDate: string | null | undefined, now: number): number | null {
  const target = dayFromIso(examDate);
  if (!target) return null;
  const today = new Date(now);
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  return Math.round((target.getTime() - startOfToday.getTime()) / MS_PER_DAY);
}

/**
 * The header's countdown under the date: "4 weeks to go", "5 days to go",
 * "Exam day", the passed message, or `undefined` when there is no date.
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

/**
 * Whether the exam falls inside the next seven days — the window in which the
 * legacy dashboard showed its one-time "Good luck this week" note.
 */
export function isExamWeek(examDate: string | null | undefined, now: number = Date.now()): boolean {
  const days = daysUntil(examDate, now);
  return days !== null && days >= 0 && days <= 7;
}
