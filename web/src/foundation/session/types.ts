import type { components } from "@/foundation/platform-client";
import type { Permission } from "@/foundation/session/permissions";

export type PlatformUser = components["schemas"]["UserRead"];
export type PlatformMembership =
  components["schemas"]["app__features__identity__schemas__MembershipRead"];
export type PlatformCapabilities = components["schemas"]["Capabilities"];

/**
 * What the app knows about the person using it.
 *
 * `can` is the backend's answer, not the browser's. The old institution client
 * kept a `b2bCapabilities.ts` that re-derived permissions from a role string,
 * which meant two implementations of one policy and a screen that could offer
 * an action the API would refuse. There is one implementation now and it is
 * the server's.
 */
export interface Session {
  user: PlatformUser;
  capabilities: PlatformCapabilities;
}

export type SessionStatus = "loading" | "authenticated" | "anonymous";

export interface SessionState {
  status: SessionStatus;
  session: Session | null;
  /** True once the first resolution has happened, however it went. */
  ready: boolean;
  /**
   * A stored token was presented and refused.
   *
   * Distinct from a first visit, which is anonymous and has never held one.
   * The login page uses it to explain the redirect; a signed-out click does not.
   */
  sessionExpired: boolean;
  /**
   * Where this tab goes after signing out on purpose, or null. Plain `/login`
   * by default: the next sign-in may be somebody else's, so the page they were
   * on is not offered back. Only on the page they signed out from (spent once
   * they leave it, and cleared when a session loads again), so a protected
   * page opened later keeps its own `next`.
   */
  signedOutTo: string | null;
  /**
   * Who this is could not be asked: `/me` failed with something other than a
   * 401 and nothing is known yet. Asked again in the background regardless;
   * a gate shows an error with a retry rather than a spinner that never ends.
   */
  unavailable: boolean;
  /** Re-reads `/me` with the tokens stored now (never a load started before them); answers the session, or null. */
  refresh: () => Promise<Session | null>;
  /** `to` is where the sign-in page should open, e.g. with a notice; `/login` otherwise. */
  signOut: (to?: string) => Promise<void>;
  /** `null` is the person's own practice. */
  selectWorkspace: (orgSlug: string | null) => Promise<void>;
}

/** Whether the backend grants this permission in the active workspace. */
export function can(session: Session | null, permission: Permission): boolean {
  return session?.capabilities.can[permission] === true;
}

export function isPlatformAdmin(session: Session | null): boolean {
  return session?.capabilities.is_platform_admin === true;
}

export function activeMembership(session: Session | null): PlatformMembership | null {
  const slug = session?.capabilities.active_org_slug;
  if (!session || !slug) return null;
  return (session.user.memberships ?? []).find((m) => m.org_slug === slug) ?? null;
}
