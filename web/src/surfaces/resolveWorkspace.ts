import type { PlatformUser } from "@/foundation/session";
import {
  PERSONAL_SLUG,
  PERSONAL_WORKSPACE,
  workspaceKind,
  type Workspace,
} from "@/foundation/routing";

type Membership = NonNullable<PlatformUser["memberships"]>[number];

function toWorkspace(membership: Membership): Workspace {
  return {
    kind: workspaceKind(membership.org_type),
    slug: membership.org_slug,
    name: membership.org_name ?? membership.org_slug,
    orgSlug: membership.org_slug,
    role: membership.role,
  };
}

/**
 * Which workspace a URL segment names, for this person.
 *
 * `/app/me` is always their own practice. `/app/<slug>` is an organisation
 * they belong to; if they do not belong to it, this answers null and the route
 * renders a 404 rather than a shell with no data in it.
 *
 * The memberships come from `/me`, which is the backend's list, so a person
 * who has been removed from an organisation stops being able to address it on
 * their next page load rather than on their next token refresh.
 */
export function resolveWorkspace(slug: string, user: PlatformUser | null): Workspace | null {
  if (slug === PERSONAL_SLUG) return PERSONAL_WORKSPACE;
  if (!user) return null;

  const membership = (user.memberships ?? []).find((m) => m.org_slug === slug);
  if (!membership) return null;

  return toWorkspace(membership);
}

/**
 * Every workspace this person can be in, their own first.
 *
 * Their own practice leads because it is the one that is always there:
 * entitlements they bought, attempts they made on their own time. An
 * institution is something they additionally belong to.
 */
export function workspacesFor(user: PlatformUser | null): Workspace[] {
  const orgs = (user?.memberships ?? []).map(toWorkspace);
  return [PERSONAL_WORKSPACE, ...orgs];
}

/**
 * Where `/app` sends somebody with no deep link: the workspace they were last
 * in, else their institution (a person who belongs to one is there to work,
 * and `me` would show them the consumer exam picker), else their own practice.
 */
export function landingWorkspace(user: PlatformUser | null, remembered: string | null): Workspace {
  const available = workspacesFor(user);
  return (
    available.find((workspace) => workspace.slug === remembered) ??
    available.find((workspace) => workspace.slug !== PERSONAL_SLUG) ??
    PERSONAL_WORKSPACE
  );
}
