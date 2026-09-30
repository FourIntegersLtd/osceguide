const STORAGE_PREFIX = "osce_onboarding_dismissed";

/** Per app track so dismissing SCA onboarding does not hide PLAB/Ortho. */
export function onboardingDismissedStorageKey(
  appType: string,
  userId: string,
): string {
  return `${STORAGE_PREFIX}:${appType}:${userId}`;
}

function scopedStorageKey(suffix: string, appType: string, userId: string): string {
  return `${STORAGE_PREFIX}:${suffix}:${appType}:${userId}`;
}

/** True if the user closed or finished onboarding and should not see the dashboard modal again. */
export function hasDismissedDashboardOnboarding(
  appType: string,
  userId: string,
): boolean {
  if (typeof window === "undefined") return false;
  return (
    localStorage.getItem(onboardingDismissedStorageKey(appType, userId)) === "1"
  );
}

export function setDashboardOnboardingDismissed(
  appType: string,
  userId: string,
): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(onboardingDismissedStorageKey(appType, userId), "1");
}

const ONBOARDING_REPLAY_APP_TYPES = new Set(["sca", "plab", "ortho"]);

export function supportsDashboardOnboardingReplay(
  appType: string | null | undefined,
): boolean {
  return Boolean(appType && ONBOARDING_REPLAY_APP_TYPES.has(appType));
}

/** Brand-new users with no mock history who have not finished/skipped onboarding. */
export function needsDashboardOnboarding(
  appType: string | null | undefined,
  userId: string | null | undefined,
  stationProgressLength: number,
): boolean {
  if (!appType || !userId) return false;
  if (stationProgressLength > 0) return false;
  return !hasDismissedDashboardOnboarding(appType, userId);
}

/** Marketplace / colleague-practice prompts should wait until onboarding is done. */
export function canShowPartnerPracticePrompts(
  appType: string | null | undefined,
  userId: string | null | undefined,
  stationProgressLength: number,
): boolean {
  return !needsDashboardOnboarding(appType, userId, stationProgressLength);
}

/** No-show standby opt-in only matters after colleague or marketplace practice. */
export function hasColleaguePracticeHistory(
  humanPracticeSessionCount: number | undefined,
  hasMarketplaceSessions: boolean,
): boolean {
  return (humanPracticeSessionCount ?? 0) > 0 || hasMarketplaceSessions;
}

export function hasDismissedMarketplaceAnnouncement(
  appType: string,
  userId: string,
): boolean {
  if (typeof window === "undefined") return false;
  return (
    localStorage.getItem(
      scopedStorageKey("marketplace_announcement", appType, userId),
    ) === "1"
  );
}

export function setMarketplaceAnnouncementDismissed(
  appType: string,
  userId: string,
): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(
    scopedStorageKey("marketplace_announcement", appType, userId),
    "1",
  );
}

export function hasDismissedPartnerStandbyPrompt(
  appType: string,
  userId: string,
): boolean {
  if (typeof window === "undefined") return false;
  return (
    localStorage.getItem(scopedStorageKey("partner_standby", appType, userId)) ===
    "1"
  );
}

export function setPartnerStandbyPromptDismissed(
  appType: string,
  userId: string,
): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(
    scopedStorageKey("partner_standby", appType, userId),
    "1",
  );
}
