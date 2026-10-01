"use client";

import {
  AsyncBoundary,
  Badge,
  Button,
  Panel,
  Row,
  RowList,
  Select,
} from "@/foundation/ui";
import { useAsync, useToast } from "@/foundation/hooks";
import {
  listOrgMembershipsForSupport,
  type Membership,
} from "@/domains/platform/api";
import {
  changeMembershipRole,
  restoreMembership,
  revokeMembership,
} from "@/domains/platform/support/api";
import { SEAT_ROLES } from "@/domains/platform/support";

export function MembersSection({ slug }: { slug: string }) {
  const state = useAsync(
    (signal) => listOrgMembershipsForSupport(slug, { limit: 50 }, signal),
    [slug],
  );

  return (
    <Panel
      title="Members"
      description="Change someone’s role, remove their access or give it back. Every change is logged, just as when the organisation’s own admins make it."
      padding="none"
    >
      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{
          title: "No members",
          description: "Nobody has joined this organisation yet.",
          bare: true,
        }}
      >
        {(page) => (
          <RowList flush>
            {page.items.map((membership) => (
              <MemberRow
                key={membership.id}
                membership={membership}
                slug={slug}
                onChanged={state.reload}
              />
            ))}
          </RowList>
        )}
      </AsyncBoundary>
    </Panel>
  );
}

function MemberRow({
  membership,
  slug,
  onChanged,
}: {
  membership: Membership;
  slug: string;
  onChanged: () => void;
}) {
  const toast = useToast();
  const run = async (work: () => Promise<unknown>, done: string) => {
    try {
      await work();
      toast.success(done);
      onChanged();
    } catch {
      toast.error("That did not work");
    }
  };
  const revoked = membership.status === "revoked";
  return (
    <Row>
      <div className="min-w-0">
        <p className="truncate text-osce-data font-medium text-ink">
          {membership.email ?? membership.user_id}
        </p>
        <p className="truncate text-osce-meta text-ink-subtle">
          {membership.role}
          {membership.product_surface ? ` · ${membership.product_surface}` : ""}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={revoked ? "neutral" : "success"}>
          {membership.status}
        </Badge>
        <Select
          aria-label="Role"
          selectSize="sm"
          className="w-auto"
          value={membership.role}
          onChange={(e) =>
            void run(
              () => changeMembershipRole(slug, membership.id, e.target.value),
              "Role changed",
            )
          }
        >
          {[...SEAT_ROLES.map((r) => r.value), "supervisor", "trainee"]
            .filter((v, i, a) => a.indexOf(v) === i)
            .map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          {SEAT_ROLES.every((r) => r.value !== membership.role) &&
          !["supervisor", "trainee"].includes(membership.role) ? (
            <option value={membership.role}>{membership.role}</option>
          ) : null}
        </Select>
        <Button
          variant={revoked ? "primary" : "danger"}
          size="sm"
          onClick={() =>
            void run(
              () =>
                revoked
                  ? restoreMembership(slug, membership.id)
                  : revokeMembership(slug, membership.id),
              revoked ? "Access restored" : "Access revoked",
            )
          }
        >
          {revoked ? "Restore" : "Revoke"}
        </Button>
      </div>
    </Row>
  );
}
