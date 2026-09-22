/**
 * The dashboard's exam-date countdown.
 *
 * Brought across from the retiring `ScaDashboard`, which computed a live
 * "time remaining" for the header pill and a coarser "N weeks until your exam"
 * for the subtitle. `users.exam_date` is a plain date (no time), so a bare
 * `YYYY-MM-DD` is read as UTC midnight — the same instant the legacy
 * `apiUtcDate` helper produced for a date with no `T` and no zone.
 *
 * These are pure so the header control can tick them every second without the
 * rest of the dashboard re-rendering, and so the subtitle can read them once.
 */

const MS_PER_MINUTE = 60 * 1000;
const MS_PER_HOUR = 60 * MS_PER_MINUTE;
const MS_PER_DAY = 24 * MS_PER_HOUR;
const MS_PER_WEEK = 7 * MS_PER_DAY;

/** The sentinel the legacy screen used for a date already behind us. */
export const EXAM_PASSED = "Exam date has passed";

/** Parse an exam date as a UTC instant, or `null` when there is none. */
export function parseExamDate(value: string | null | undefined): Date | null {
  if (value == null) return null;
  const text = String(value).trim();
  if (!text) return null;
  const zoned = /[zZ]$/.test(text) || /[+-]\d{2}:?\d{2}$/.test(text);
  const date = zoned ? new Date(text) : new Date(text.includes("T") ? `${text}Z` : text);
  return Number.isFinite(date.getTime()) ? date : null;
}

/**
 * The header pill's live countdown: "5 days 3 hours", "4h", "Less than 1h",
 * "Less than 1m", or `EXAM_PASSED`. `null` when there is no date to count to.
 */
export function examTimeRemaining(
  examDate: string | null | undefined,
  now: number = Date.now(),
): string | null {
  const target = parseExamDate(examDate);
  if (!target) return null;
  const difference = target.getTime() - now;
  if (difference <= 0) return EXAM_PASSED;

  const days = Math.floor(difference / MS_PER_DAY);
  const hours = Math.floor((difference / MS_PER_HOUR) % 24);
  const minutes = Math.floor((difference / MS_PER_MINUTE) % 60);

  if (days > 0) return hours > 0 ? `${days} days ${hours} hours` : `${days} days`;
  if (hours > 0) return `${hours}h`;
  if (minutes > 0) return "Less than 1h";
  return "Less than 1m";
}

/**
 * The subtitle's countdown: "N week(s) until your exam", the passed message, or
 * `undefined` when there is nothing to say (no date, or less than a week away
 * and not passed — the legacy screen left the subtitle empty in that window).
 */
export function examCountdownSubtitle(
  examDate: string | null | undefined,
  now: number = Date.now(),
): string | undefined {
  const timeRemaining = examTimeRemaining(examDate, now);
  if (!examDate || !timeRemaining) return undefined;
  if (timeRemaining === EXAM_PASSED) {
    return "Your exam date has passed. Keep practising to stay sharp.";
  }
  const target = parseExamDate(examDate);
  if (!target) return undefined;
  const weeks = Math.ceil((target.getTime() - now) / MS_PER_WEEK);
  if (weeks <= 0) return undefined;
  return `${weeks} week${weeks === 1 ? "" : "s"} until your exam`;
}

/**
 * Whether the exam falls inside the next seven days — the window in which the
 * legacy dashboard showed its one-time "Good luck this week" note.
 */
export function isExamWeek(examDate: string | null | undefined, now: number = Date.now()): boolean {
  const target = parseExamDate(examDate);
  if (!target) return false;
  const diffDays = Math.floor((target.getTime() - now) / MS_PER_DAY);
  return diffDays >= 0 && diffDays <= 7;
}
