"use client";

import { Discussion } from "@/capabilities/community";
import { useSession } from "@/foundation/session";
import { useAsync } from "@/foundation/hooks";
import { AsyncBoundary } from "@/foundation/ui";
import { readOrgDashboard } from "@/domains/assess/api";
import { useSurface } from "@/capabilities";

/**
 * The shared discussion capability, scoped to this organisation.
 *
 * The capability takes an organisation id and knows nothing else about
 * institutions; supplying it is the arm's job, which is why this thin wrapper
 * lives in `domains/assess` rather than inside the capability.
 */
export function OrgDiscussion() {
  const { orgSlug } = useSurface();
  const { session } = useSession();

  const org = useAsync(
    async (signal) => (orgSlug ? readOrgDashboard(orgSlug, signal) : null),
    [orgSlug, session?.capabilities.active_org_slug],
  );

  return (
    <AsyncBoundary state={org}>
      {(data) => <Discussion orgId={data?.org_id ?? null} />}
    </AsyncBoundary>
  );
}
