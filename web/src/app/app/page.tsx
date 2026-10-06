"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Spinner } from "@/foundation/ui";
import { isPlatformAdmin, RequireSession, useSession } from "@/foundation/session";
import { workspaceBasePath } from "@/foundation/routing";
import { lastWorkspace } from "@/foundation/routing/lastWorkspace";
import { landingWorkspace } from "@/surfaces";

/**
 * `/app` on its own: send them where they were.
 *
 * Where you were last; failing that your institution if you belong to one
 * (landing on `me` showed them the consumer exam picker); else your own practice.
 * Platform staff go to `/staff`.
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
    // Platform staff have a console rather than a workspace; their own
    // practice is one link away from it.
    if (isPlatformAdmin(session)) {
      router.replace("/staff");
      return;
    }
    router.replace(workspaceBasePath(landingWorkspace(session?.user ?? null, lastWorkspace())));
  }, [ready, session, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Spinner label="Loading" />
    </div>
  );
}
