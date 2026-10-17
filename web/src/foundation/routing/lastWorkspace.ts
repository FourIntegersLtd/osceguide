import { isWorkspaceSlug } from "@/foundation/routing/workspace";

/**
 * The workspace this person was in last, remembered across visits.
 *
 * Somebody who works inside one institution should not have to choose it every
 * morning, and somebody who mostly practises on their own should not be
 * dropped into a trust because it happens to be first in a list. The value is
 * a hint only: `/app` checks it against the memberships the backend returns
 * before following it, so a stale slug from an organisation they have left
 * sends them to their own practice rather than to a 404. It is kept per
 * account: one browser shared by two people sent an institution admin to the
 * personal practice the learner before them had last used.
 */
const key = (userId: string) => `osce_last_workspace:${userId}`;

export function lastWorkspace(userId: string): string | null {
  try {
    const value = window.localStorage.getItem(key(userId));
    return value && isWorkspaceSlug(value) ? value : null;
  } catch {
    // Safari in private mode throws on access rather than returning null.
    return null;
  }
}

export function rememberWorkspace(userId: string, slug: string): void {
  try {
    window.localStorage.setItem(key(userId), slug);
  } catch {
    // Not remembering is a smaller failure than not rendering.
  }
}
