/** What the foot of the sidebar shows for the exam: a switcher, a retry, or nothing. */
export function examSwitcherView(input: { consumer: boolean; codes: readonly string[]; error: Error | null }): "switcher" | "failed" | "none" {
  if (!input.consumer) return "none";
  if (input.codes.length > 1) return "switcher";
  return input.error ? "failed" : "none";
}
