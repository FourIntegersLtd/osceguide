import { sanitizeReturnTo } from "@/foundation/session/returnTo";

/**
 * Who last held a session in this tab, so a sign-in after it ended can tell
 * whether `?next=` was theirs. Per tab (sessionStorage), like the page it guards.
 */
const SESSION_USER_KEY = "osce_session_user";

export function lastSessionUser(): string | null {
  try {
    return window.sessionStorage.getItem(SESSION_USER_KEY);
  } catch {
    return null;
  }
}

/** `null` forgets: a deliberate sign-out leaves nothing to return to. */
export function rememberSessionUser(userId: string | null): void {
  try {
    if (userId) window.sessionStorage.setItem(SESSION_USER_KEY, userId);
    else window.sessionStorage.removeItem(SESSION_USER_KEY);
  } catch {
    // Not remembering only means a returning person lands on their home page.
  }
}

/**
 * Where `/login?next=` (or `returnTo`) sends whoever just signed in, if it is
 * theirs. A session that ended in this tab leaves its page there; somebody
 * else signing in on that form goes to their own landing instead of into
 * another person's workspace.
 */
export function nextAfterSignIn(params: URLSearchParams, previousUserId: string | null, userId: string): string | null {
  if (previousUserId && previousUserId !== userId) return null;
  return sanitizeReturnTo(params.get("next") ?? params.get("returnTo"));
}
