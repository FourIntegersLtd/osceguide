import type { components } from "@/foundation/platform-client";

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
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
  selectWorkspace: (orgSlug: string) => Promise<void>;
}

/** Whether the backend grants this permission in the active workspace. */
export function can(session: Session | null, permission: string): boolean {
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
