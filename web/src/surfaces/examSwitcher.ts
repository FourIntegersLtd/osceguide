import { examCountdown } from "@/foundation/ui/examCountdown";

/** What the foot of the sidebar shows for the exam: a switcher, a retry, or nothing. */
export function examSwitcherView(input: { consumer: boolean; codes: readonly string[]; error: Error | null }): "switcher" | "failed" | "none" {
  if (!input.consumer) return "none";
  if (input.codes.length > 1) return "switcher";
  return input.error ? "failed" : "none";
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
