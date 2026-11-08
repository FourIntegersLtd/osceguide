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
 * `/app/me` is the training workspace: every signed-in person has one, institution
 * members included, so it resolves for all of them. If they do not belong to the
 * workspace this answers null and the route renders a 404 with a way to their
 * landing workspace, rather than a shell with no data in it.
 *
 * The memberships come from `/me`, which is the backend's list, so a person
 * who has been removed from an organisation stops being able to address it on
 * their next page load rather than on their next token refresh.
 */
export function resolveWorkspace(slug: string, user: PlatformUser | null): Workspace | null {
  if (slug === PERSONAL_SLUG && !user) return PERSONAL_WORKSPACE;
  return workspacesFor(user).find((workspace) => workspace.slug === slug) ?? null;
}

/**
 * Every workspace this person can be offered, training first.
 *
 * Training is everyone's own practice, so a member is offered it beside their
 * institutions. The console is a separate row the switcher adds for platform
 * admins, not a workspace.
 */
export function workspacesFor(user: PlatformUser | null): Workspace[] {
  return [PERSONAL_WORKSPACE, ...(user?.memberships ?? []).map(toWorkspace)];
}

/**
 * Where `/app` sends somebody with no deep link: the workspace they were last
 * in, else their institution (a person who belongs to one is there to work,
 * and `me` would show them the consumer exam picker), else their own practice.
 */
export function landingWorkspace(
  user: PlatformUser | null,
  remembered: string | null,
): Workspace {
  const available = workspacesFor(user);
  return (
    available.find((workspace) => workspace.slug === remembered) ??
    available.find((workspace) => workspace.slug !== PERSONAL_SLUG) ??
    PERSONAL_WORKSPACE
  );
}
