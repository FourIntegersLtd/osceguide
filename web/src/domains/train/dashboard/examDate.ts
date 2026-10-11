import { daysUntil } from "@/foundation/ui/examCountdown";

/**
 * Whether the exam falls inside the next seven days — the window in which the
 * legacy dashboard showed its one-time "Good luck this week" note.
 */
export function isExamWeek(examDate: string | null | undefined, now: number = Date.now()): boolean {
  const days = daysUntil(examDate, now);
  return days !== null && days >= 0 && days <= 7;
}
