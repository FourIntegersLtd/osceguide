import { examCountdown } from "@/foundation/ui/examCountdown";

/** True when the foot of the sidebar should offer a retry: the exams could not be read and none are known. */
export function examsFailedToLoad(input: { consumer: boolean; codes: readonly string[]; error: Error | null }): boolean {
  return input.consumer && input.codes.length === 0 && input.error !== null;
}

/**
 * The line under the workspace name: the exam, with the countdown once a date is set
 * ("SCA · 6 weeks to go"). The one place the countdown shows in the shell.
 */
export function examDetail(code: string | null, examDate: string | null, now: Date = new Date()): string | null {
  if (!code) return null;
  const label = code.toUpperCase();
  const countdown = examCountdown(examDate, now.getTime());
  return countdown ? `${label} · ${countdown}` : label;
}
