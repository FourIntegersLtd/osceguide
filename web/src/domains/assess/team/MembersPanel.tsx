"use client";

import { useState } from "react";
import { Alert, Button, EmptyState, b2bTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { Dialog } from "@/domains/assess/team/chrome";
import {
  changeMemberRole,
  restoreMembership,
  revokeMembership,
  type Membership,
} from "@/domains/assess/team/api";
import {
  ASSIGNABLE_ROLES,
  ROLE_DESCRIPTIONS,
  isActive,
  isLastAdmin,
  isOwner,
  roleLabel,
  sortMembers,
  staffCountLabel,
} from "@/domains/assess/team/support";

const TABLE_CLASS = "min-w-full w-full divide-y divide-b2b-border";
const CELL = "px-4 py-3 text-osce-body align-middle";

type Pending =
  | { kind: "role"; member: Membership }
  | { kind: "revoke"; member: Membership }
  | { kind: "restore"; member: Membership }
  | null;

/**
 * The organisation's staff.
 *
 * Revoked memberships stay on the list rather than disappearing, because the
 * backend revokes rather than deletes — the record of who had access and when
 * is the point — and a screen that hid them would make "restore" unreachable.
 */
export function MembersPanel({
  orgSlug,
  members,
  canManage,
  onChanged,
}: {
  orgSlug: string;
  members: Membership[];
  canManage: boolean;
  onChanged: () => void;
}) {
  const rows = sortMembers(members);
  const [pending, setPending] = useState<Pending>(null);
  const [role, setRole] = useState<string>("supervisor");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function open(next: NonNullable<Pending>) {
    setError(null);
    if (next.kind === "role") setRole(next.member.role);
    setPending(next);
  }

  async function commit() {
    if (!pending) return;
    setBusy(true);
    setError(null);
    const who = pending.member.email ?? "this person";
    try {
      if (pending.kind === "role") {
        await changeMemberRole(orgSlug, pending.member.id, role);
        setNotice(`${who} is now ${roleLabel(role).toLowerCase()}.`);
      } else if (pending.kind === "revoke") {
        await revokeMembership(orgSlug, pending.member.id);
        setNotice(`Revoked access for ${who}.`);
      } else {
        await restoreMembership(orgSlug, pending.member.id);
        setNotice(`Restored access for ${who}.`);
      }
      setPending(null);
      onChanged();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  if (rows.length === 0) {
    return (
      <EmptyState
        title="No staff yet"
        description="Invite a supervisor so somebody can run a circuit."
      />
    );
  }

  return (
    <div className="min-w-0 space-y-4">
      {notice ? <Alert tone="success">{notice}</Alert> : null}
      <p className={b2bTokens.b2bEyebrow}>{staffCountLabel(rows.length)}</p>

      <div className={b2bTokens.b2bGroupedShell}>
        <div className={b2bTokens.b2bTableScroll}>
          <table className={TABLE_CLASS}>
            <thead>
              <tr>
                {["Email", "Role", "Access", ""].map((header, index) => (
                  <th
                    key={header || index}
                    scope="col"
                    className="px-4 py-2 text-left text-osce-caption font-medium text-b2b-mid"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-b2b-border">
              {rows.map((member) => (
                <tr key={member.id}>
                  <td className={`${CELL} min-w-[12rem]`}>
                    {/* The list endpoint does not carry the address — only the
                        invite response does (see docs/port-gaps.md) — so a row
                        says so rather than printing a raw uuid as a name. */}
                    <span className="font-medium text-b2b-headline">
                      {member.email ?? "Account without a listed address"}
                    </span>
                    {member.email ? null : (
                      <span className="ml-2 font-mono text-osce-caption text-b2b-icon">
                        {member.user_id.slice(0, 8)}
                      </span>
                    )}
                    {member.invited ? (
                      <span className="ml-2 text-osce-caption text-b2b-mid">Invited</span>
                    ) : null}
                  </td>
                  <td className={`${CELL} min-w-[6rem] text-b2b-graphite`}>
                    {roleLabel(member.role)}
                  </td>
                  <td className={`${CELL} min-w-[5rem]`}>
                    {isActive(member) ? (
                      <span className="text-osce-caption font-medium text-b2b-success-text">
                        Active
                      </span>
                    ) : (
                      <span className="text-osce-caption font-medium text-b2b-warning-text/90">
                        Revoked
                      </span>
                    )}
                  </td>
                  <td className={`${CELL} text-right`}>
                    {canManage ? (
                      <RowActions
                        member={member}
                        lastAdmin={isLastAdmin(member, rows)}
                        onAction={open}
                      />
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {!canManage ? (
        <p className="text-osce-caption text-b2b-icon">
          Contact an owner or admin to change who has access.
        </p>
      ) : null}

      <Dialog
        open={pending?.kind === "role"}
        title="Change role"
        lead={pending ? `${pending.member.email ?? "This person"}'s role in this organisation.` : ""}
        error={error}
        busy={busy}
        commitLabel="Save role"
        busyLabel="Saving…"
        onClose={() => setPending(null)}
        onCommit={() => void commit()}
      >
        <div>
          <label
            htmlFor="assess-member-role"
            className="block text-osce-body font-semibold text-b2b-headline"
          >
            Their role
          </label>
          <p className="mt-0.5 text-osce-caption text-b2b-mid">
            {ROLE_DESCRIPTIONS.supervisor} {ROLE_DESCRIPTIONS.admin}
          </p>
          <select
            id="assess-member-role"
            value={role}
            onChange={(event) => setRole(event.target.value)}
            className={`mt-2 ${b2bTokens.b2bInputBase}`}
          >
            {ASSIGNABLE_ROLES.map((value) => (
              <option key={value} value={value}>
                {roleLabel(value)}
              </option>
            ))}
          </select>
        </div>
      </Dialog>

      <Dialog
        open={pending?.kind === "revoke"}
        title="Revoke access"
        lead={
          pending
            ? `${pending.member.email ?? "This person"} will lose access to this organisation. Nothing they have marked is deleted.`
            : ""
        }
        error={error}
        busy={busy}
        tone="danger"
        commitLabel="Revoke access"
        busyLabel="Revoking…"
        onClose={() => setPending(null)}
        onCommit={() => void commit()}
      />

      <Dialog
        open={pending?.kind === "restore"}
        title="Restore access"
        lead={
          pending
            ? `${pending.member.email ?? "This person"} will be able to sign in to this organisation again, with the role they had.`
            : ""
        }
        error={error}
        busy={busy}
        commitLabel="Restore access"
        busyLabel="Restoring…"
        onClose={() => setPending(null)}
        onCommit={() => void commit()}
      />
    </div>
  );
}

function RowActions({
  member,
  lastAdmin,
  onAction,
}: {
  member: Membership;
  lastAdmin: boolean;
  onAction: (pending: NonNullable<Pending>) => void;
}) {
  const owner = isOwner(member);
  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      {!owner ? (
        <Button
          themeType="b2b"
          variant="secondary"
          size="sm"
          onClick={() => onAction({ kind: "role", member })}
        >
          Change role
        </Button>
      ) : null}
      {isActive(member) ? (
        <Button
          themeType="b2b"
          variant="secondary"
          size="sm"
          disabled={owner || lastAdmin}
          title={
            owner
              ? "An organisation's owner cannot be revoked here"
              : lastAdmin
                ? "Cannot revoke the last administrator"
                : undefined
          }
          onClick={() => onAction({ kind: "revoke", member })}
        >
          Revoke
        </Button>
      ) : (
        <Button
          themeType="b2b"
          variant="secondary"
          size="sm"
          onClick={() => onAction({ kind: "restore", member })}
        >
          Restore
        </Button>
      )}
    </div>
  );
}
