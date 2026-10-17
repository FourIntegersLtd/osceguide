"use client";

import { can, RequireSession, useSession } from "@/foundation/session";
import { workspaceBasePath } from "@/foundation/routing";
import { lastWorkspace } from "@/foundation/routing/lastWorkspace";
import { Redirecting } from "@/foundation/routing/Redirecting";
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
  // Platform staff have a console rather than a workspace. The same check as
  // the staff layout's gate, so the two can never send each other back.
  const to = !ready
    ? null
    : can(session, "administer_platform")
      ? "/staff"
      : workspaceBasePath(landingWorkspace(session?.user ?? null, session ? lastWorkspace(session.user.id) : null));
  return <Redirecting to={to} />;
}
