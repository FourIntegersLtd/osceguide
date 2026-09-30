const KEY = "platform.onboarding.seen";

/**
 * Whether this browser has already been through the walkthrough.
 *
 * Deliberately local rather than a field on the user: it decides whether a
 * dashboard offers the introduction, and being offered it twice on a new
 * device is a smaller harm than a migration and a write on every dashboard
 * load. The retiring client kept the same flag per exam and per user; one key
 * is enough here because the walkthrough is the same introduction whichever
 * exam renders its scenes.
 */
export function hasSeenOnboarding(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(KEY) === "1";
  } catch {
    return false;
  }
}

export function rememberOnboardingSeen(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(KEY, "1");
  } catch {
    // Private browsing refuses storage; showing the introduction again is the
    // harmless outcome and is better than failing the page.
  }
}
