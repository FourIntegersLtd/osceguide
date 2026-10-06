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
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import {
  listOrgMembershipsForSupport,
  type Membership,
} from "@/domains/platform/api";
import {
  changeMembershipRole,
  restoreMembership,
  revokeMembership,
} from "@/domains/platform/support/api";
import { roleLabel } from "@/foundation/session/roles";
import { MEMBER_ROLES, humanise, oneOptionPerLabel, rolesForOrgType } from "@/domains/platform/support";

export function MembersSection({ slug, orgType }: { slug: string; orgType: string }) {
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
                orgType={orgType}
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
  orgType,
  onChanged,
}: {
  membership: Membership;
  slug: string;
  orgType: string;
  onChanged: () => void;
}) {
  // The member's own role stays in the menu even where it does not fit the type.
  const fitting = rolesForOrgType(MEMBER_ROLES, orgType);
  if (!fitting.includes(membership.role)) fitting.push(membership.role);
  const roles = oneOptionPerLabel(fitting, [membership.role, "institution_admin", "partner_admin"]);
  const toast = useToast();
  const run = async (work: () => Promise<unknown>, done: string) => {
    try {
      await work();
      toast.success(done);
      onChanged();
    } catch (cause) {
      // The server's reason, e.g. that this is the organisation's last administrator.
      toast.error(errorMessage(cause));
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
          {roleLabel(membership.role, humanise(membership.role))}
          {membership.product_surface ? ` · ${humanise(membership.product_surface)}` : ""}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={revoked ? "neutral" : "success"}>
          {humanise(membership.status)}
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
          {roles.map((value) => (
            <option key={value} value={value}>
              {roleLabel(value, humanise(value))}
            </option>
          ))}
        </Select>
        <Button
          variant={revoked ? "primary" : "danger"}
          size="sm"
          onClick={() =>
            run(
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
