"use client";

import {
  AsyncBoundary,
  Badge,
  Button,
  Select,
} from "@/foundation/ui";
import Table, { type Column } from "@/foundation/table/Table";
import { errorMessage, useCursorPages, useToast } from "@/foundation/hooks";
import {
  listOrgMembershipsForSupport,
  type Membership,
} from "@/domains/platform/api";
import {
  changeMembershipRole,
  resendMembershipInvitation,
  restoreMembership,
  revokeMembership,
} from "@/domains/platform/support/api";
import { roleLabel } from "@/foundation/session/roles";
import { humanise } from "@/foundation/format";
import { MEMBER_ROLES, oneOptionPerLabel, rolesForOrgType } from "@/domains/platform/support";

/** The member row with the fields the api now sends; until the schema is regenerated. */
type SupportMember = Membership & { must_change_password?: boolean };

export function MembersSection({ slug, orgType }: { slug: string; orgType: string }) {
  const pages = useCursorPages(
    (cursor, signal) => listOrgMembershipsForSupport(slug, { limit: 50, cursor }, signal),
    [slug],
  );
  const columns: Column<SupportMember>[] = [
    {
      header: "Member",
      key: "email",
      priority: "primary",
      render: (membership) => (
        <div className="min-w-0">
          <p className="truncate font-medium text-ink">{membership.email ?? membership.user_id}</p>
          <p className="truncate text-osce-meta text-ink-subtle">
            {roleLabel(membership.role, humanise(membership.role))}
            {membership.product_surface ? ` · ${humanise(membership.product_surface)}` : ""}
          </p>
        </div>
      ),
    },
    {
      header: "Status",
      key: "status",
      render: (membership) => (
        <div className="flex flex-wrap items-center gap-2">
          <Badge dot tone={membership.status === "revoked" ? "neutral" : "success"}>
            {humanise(membership.status)}
          </Badge>
          {membership.invited ? <Badge tone="warning">Invited, not signed in</Badge> : null}
          {membership.must_change_password && !membership.invited ? (
            <Badge tone="warning">Temporary password</Badge>
          ) : null}
        </div>
      ),
    },
    {
      header: "Actions",
      key: "id",
      render: (membership) => (
        <MemberActions
          membership={membership}
          slug={slug}
          orgType={orgType}
          onChanged={pages.state.reload}
        />
      ),
    },
  ];

  return (
    <AsyncBoundary state={pages.state}>
      {(items) => (
        <Table<SupportMember>
          rows={items}
          more={pages}
          themeType="b2b"
          idField="id"
          title="Members"
          description="Change someone’s role, remove their access or give it back. Every change is logged, just as when the organisation’s own admins make it."
          empty={{
            title: "No members",
            description: "No staff have joined this organisation yet. Trainees are managed on its roster.",
          }}
          columns={columns}
        />
      )}
    </AsyncBoundary>
  );
}

function MemberActions({
  membership,
  slug,
  orgType,
  onChanged,
}: {
  membership: SupportMember;
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
    <div className="flex flex-wrap items-center gap-2">
      {membership.invited && !revoked ? (
        <Button
          variant="secondary"
          size="sm"
          onClick={() =>
            run(() => resendMembershipInvitation(slug, membership.id), "Invitation sent again")
          }
        >
          Resend invitation
        </Button>
      ) : null}
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
        themeType="b2b" variant={revoked ? "commit" : "danger"}
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
  );
}
