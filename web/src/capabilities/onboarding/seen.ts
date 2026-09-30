const STORAGE_PREFIX = "osce_onboarding_dismissed";

/**
 * Whether this person has finished or closed the walkthrough, per exam and per
 * user — the exact semantics and key the retiring client used
 * (`osce_onboarding_dismissed:{examCode}:{userId}`), so dismissing the SCA
 * onboarding never hides another exam's, and two accounts on one browser do
 * not share the flag.
 */
export function onboardingDismissedStorageKey(examCode: string, userId: string): string {
  return `${STORAGE_PREFIX}:${examCode}:${userId}`;
}

export function hasSeenOnboarding(examCode: string, userId: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(onboardingDismissedStorageKey(examCode, userId)) === "1";
  } catch {
    return false;
  }
}

export function rememberOnboardingSeen(examCode: string, userId: string): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(onboardingDismissedStorageKey(examCode, userId), "1");
  } catch {
    // Private browsing refuses storage; showing the introduction again is the
    // harmless outcome and is better than failing the page.
  }
}

/**
 * Brand-new users with no marked work who have not finished or closed the
 * walkthrough — the retiring dashboard's trigger for opening onboarding as a
 * modal over the dashboard.
 */
export function needsDashboardOnboarding(
  examCode: string | null | undefined,
  userId: string | null | undefined,
  attempts: number,
): boolean {
  if (!examCode || !userId) return false;
  if (attempts > 0) return false;
  return !hasSeenOnboarding(examCode, userId);
}
