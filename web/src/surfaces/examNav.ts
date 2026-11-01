import { examCountdown } from "@/foundation/ui/examCountdown";

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

/**
 * The exam the nav and route gates filter exam-specific capabilities by. While the dashboard is
 * loading, "" (hide them rather than flash them); once it has answered with no exam or failed,
 * `undefined` (filter nothing). A missing answer is not evidence that the exam lacks a capability,
 * and treating it so rendered a failed dashboard load as a 404 on the Marketplace.
 */
export function examForFilter(input: { code: string | null; loading: boolean }): string | undefined {
  return input.code ?? (input.loading ? "" : undefined);
}
