"use client";

import { use, useEffect, useSyncExternalStore } from "react";
import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { Spinner } from "@/foundation/ui";
import { RequireSession, useSession } from "@/foundation/session";
import { OrganisationSuspended } from "@/foundation/session/OrganisationSuspended";
import { isOrgSuspended, subscribeOrgSuspension } from "@/foundation/platform-client/orgSuspension";
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
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label="Loading" />
      </div>
    );
  }

  const workspace = resolveWorkspace(slug, session?.user ?? null);
  if (!workspace) notFound();

  return <Frame workspace={workspace}>{children}</Frame>;
}

function Frame({ workspace, children }: { workspace: Workspace; children: ReactNode }) {
  // Remembered so `/app` and the next visit land where they left off, rather
  // than in whichever workspace happens to be first in a list.
  useEffect(() => {
    rememberWorkspace(workspace.slug);
  }, [workspace.slug]);
  // The first `organization_suspended` from any panel replaces the whole shell.
  const suspended = useSyncExternalStore(
    subscribeOrgSuspension,
    () => isOrgSuspended(workspace.slug),
    () => false,
  );
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
