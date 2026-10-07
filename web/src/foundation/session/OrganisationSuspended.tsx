"use client";

import { useSyncExternalStore } from "react";
import { Button, EmptyState } from "@/foundation/ui";
import { isOrgSuspended, subscribeOrgSuspension } from "@/foundation/platform-client/orgSuspension";
import { useSession } from "@/foundation/session/SessionProvider";

/**
 * What a member of a suspended organisation sees instead of its workspace.
 *
 * Signing in still works (the suspension is on the organisation, not the
 * person), but every org route answers `organization_suspended`, and the
 * shell used to render each panel's raw 403 (F-1). One screen says what
 * happened and who can change it.
 */
export function OrganisationSuspended({ name }: { name: string }) {
  const { signOut } = useSession();
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md">
        <EmptyState
          title={`${name} is suspended`}
          description="Your organisation's access to OSCE Guide has been paused, so its sittings, results and people cannot be opened. Your own account is fine. Contact your organisation to have access restored."
          action={
            <Button variant="secondary" onClick={() => void signOut()}>
              Sign out
            </Button>
          }
        />
      </div>
    </main>
  );
}

/** Whether platform-api has refused this organisation as suspended this page
 *  load; the first refusal from any panel re-renders whoever asks. */
export function useOrgSuspended(slug: string): boolean {
  return useSyncExternalStore(subscribeOrgSuspension, () => isOrgSuspended(slug), () => false);
}
