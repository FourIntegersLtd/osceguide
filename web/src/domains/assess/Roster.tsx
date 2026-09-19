"use client";

import { AsyncBoundary, Badge, Card, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { listMemberships, listTrainees, type Trainee } from "@/domains/assess/api";

/** A trainee exists before they have ever signed in, so a name may be absent. */
function fullName(trainee: Trainee): string | null {
  const parts = [trainee.first_name, trainee.last_name].filter(Boolean);
  return parts.length > 0 ? parts.join(" ") : null;
}

/** Who the organisation teaches. */
export function Trainees({ orgSlug }: { orgSlug: string }) {
  const state = useAsync((signal) => listTrainees(orgSlug, signal), [orgSlug]);
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Trainees" description="Everyone your organisation is teaching." />
      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{ title: "No trainees yet", description: "Add them to roster them onto a sitting." }}
      >
        {(page) => (
          <Card>
            <ul className="divide-y divide-border">
              {page.items.map((trainee) => (
                <li
                  key={trainee.id}
                  className="flex flex-wrap items-center justify-between gap-3 py-3"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink">
                      {fullName(trainee) ?? trainee.email}
                    </p>
                    <p className="truncate text-xs text-ink-subtle">{trainee.email}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={trainee.access_revoked ? "danger" : "success"}>
                      {trainee.access_revoked ? "Revoked" : "Active"}
                    </Badge>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </AsyncBoundary>
    </div>
  );
}

/** Staff: who may run and mark. */
export function Team({ orgSlug }: { orgSlug: string }) {
  const state = useAsync((signal) => listMemberships(orgSlug, signal), [orgSlug]);
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Team" description="Who can run sittings and mark in this workspace." />
      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{ title: "No staff yet" }}
      >
        {(page) => (
          <Card>
            <ul className="divide-y divide-border">
              {page.items.map((membership) => (
                <li
                  key={membership.id}
                  className="flex flex-wrap items-center justify-between gap-3 py-3"
                >
                  <p className="truncate text-sm text-ink">
                    {membership.email ?? membership.user_id}
                  </p>
                  <div className="flex items-center gap-2">
                    {membership.invited && <Badge tone="warning">Invited</Badge>}
                    <Badge tone="accent">{membership.role}</Badge>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </AsyncBoundary>
    </div>
  );
}
