import { dayFromIso } from "@/foundation/ui/dateDay";

/** What the foot of the sidebar shows for the exam: a switcher, a retry, or nothing. */
export function examSwitcherView(input: { consumer: boolean; codes: readonly string[]; error: Error | null }): "switcher" | "failed" | "none" {
  if (!input.consumer) return "none";
  if (input.codes.length > 1) return "switcher";
  return input.error ? "failed" : "none";
}

/**
 * The line under the workspace name: the exam, with the weeks left once a date is set
 * ("SCA · 6 weeks to exam"). The one place the countdown shows in the shell.
 */
export function examDetail(code: string | null, examDate: string | null, now: Date = new Date()): string | null {
  if (!code) return null;
  const label = code.toUpperCase();
  const day = dayFromIso(examDate);
  if (!day) return label;
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const days = Math.round((day.getTime() - today.getTime()) / 86_400_000);
  if (days < 0) return `${label} · exam passed`;
  if (days === 0) return `${label} · exam today`;
  if (days < 7) return `${label} · ${days} ${days === 1 ? "day" : "days"} to exam`;
  const weeks = Math.round(days / 7);
  return `${label} · ${weeks} ${weeks === 1 ? "week" : "weeks"} to exam`;
}
