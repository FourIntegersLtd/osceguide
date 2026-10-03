/**
 * What the live-marking column says before anything has been covered.
 *
 * The backend answers `supported=false` both for a rubric with no live domains
 * and for an attempt whose rubric is not frozen yet (that happens when the
 * patient's worker joins). Until the patient has joined, "not available" may
 * be wrong, and on staging it sat beside cards that arrived later
 * (2026-10-03), so it is only said once support is known.
 */
export function coverageEmptyMessage({
  supported,
  isLive,
  supportKnown,
}: {
  supported: boolean | null;
  isLive: boolean;
  supportKnown: boolean;
}): string {
  if (supported === false && supportKnown) {
    return "Live marking isn't available for this station. Your feedback comes at the end.";
  }
  return isLive
    ? "Listening. Things you cover will appear here as you go."
    : "Your consultation will be marked here as it happens.";
}
