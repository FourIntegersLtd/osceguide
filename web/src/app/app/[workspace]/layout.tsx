"use client";

import { use, useEffect } from "react";
import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { PageSpinner } from "@/foundation/ui";
import { RequireSession, useSession } from "@/foundation/session";
import { OrganisationSuspended, useOrgSuspended } from "@/foundation/session/OrganisationSuspended";
import { rememberWorkspace, workspaceBasePath, type Workspace } from "@/foundation/routing";
import { SurfaceShell, resolveWorkspace, surfaceForWorkspace } from "@/surfaces";

/**
 * Every signed-in screen, whichever arm it belongs to.
 *
 * One layout for all of them because a workspace is one kind of thing: the
 * slug says which one, the person's memberships say what it is, and the
 * manifest for that kind says which shell to render. There is no route prefix
 * per arm and no `switch` — see ADR 0002.
 *
 * A slug this person does not belong to is a 404 rather than an empty shell.
 * Rendering the frame around "nothing here" invites people to believe the
 * organisation exists and they are simply between permissions.
 */
export default function WorkspaceLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ workspace: string }>;
}) {
  const { workspace: slug } = use(params);
  return (
    <RequireSession>
      <Resolved slug={slug}>{children}</Resolved>
    </RequireSession>
  );
}

function Resolved({ slug, children }: { slug: string; children: ReactNode }) {
  const { session, ready } = useSession();

  if (!ready) {
    return <PageSpinner />;
  }

  const workspace = resolveWorkspace(slug, session?.user ?? null);
  if (!workspace) notFound();

  return <Frame workspace={workspace} userId={session?.user.id ?? null}>{children}</Frame>;
}

function Frame({ workspace, userId, children }: { workspace: Workspace; userId: string | null; children: ReactNode }) {
  // Remembered so `/app` and the next visit land where they left off, rather
  // than in whichever workspace happens to be first in a list.
  useEffect(() => {
    if (userId) rememberWorkspace(userId, workspace.slug);
  }, [userId, workspace.slug]);
  // The first `organization_suspended` from any panel replaces the whole shell.
  const suspended = useOrgSuspended(workspace.slug);
  if (suspended) return <OrganisationSuspended name={workspace.name} />;

  return (
    <SurfaceShell
      manifest={surfaceForWorkspace(workspace)}
      workspace={workspace}
      basePath={workspaceBasePath(workspace)}
    >
      {children}
    </SurfaceShell>
  );
}
