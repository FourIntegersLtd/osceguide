"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Spinner } from "@/foundation/ui";
import { RequireSession, useSession } from "@/foundation/session";
import { PERSONAL_SLUG, workspaceBasePath } from "@/foundation/routing";
import { lastWorkspace } from "@/foundation/routing/lastWorkspace";
import { workspacesFor } from "@/surfaces";

/**
 * `/app` on its own: send them where they were.
 *
 * The old front door decided this from memberships and always chose an
 * organisation, which is why somebody who belonged to a trust could not reach
 * their own practice at all. The rule now is simply "where you were last", and
 * failing that your own practice — because that is the workspace everyone has.
 */
export default function AppIndex() {
  return (
    <RequireSession>
      <Redirect />
    </RequireSession>
  );
}

function Redirect() {
  const { session, ready } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!ready) return;
    const available = workspacesFor(session?.user ?? null);
    const remembered = lastWorkspace();
    const target =
      available.find((workspace) => workspace.slug === remembered) ??
      available.find((workspace) => workspace.slug === PERSONAL_SLUG) ??
      available[0];
    router.replace(target ? workspaceBasePath(target) : `/app/${PERSONAL_SLUG}`);
  }, [ready, session, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Spinner label="Loading" />
    </div>
  );
}
