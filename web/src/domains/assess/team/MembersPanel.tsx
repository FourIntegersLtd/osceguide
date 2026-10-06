"use client";

import { useMemo, useState } from "react";
import { Alert, Badge, Button, EmptyState, PlatformFilterBar, PlatformFilterSearch, b2bTokens } from "@/foundation/ui";
import Table from "@/foundation/table/Table";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import { errorMessage, useCursorPages, useSearchQuery } from "@/foundation/hooks";
import { Dialog } from "@/domains/assess/team/chrome";
import {
  changeMemberRole,
  listMemberships,
  resendInvitation,
  resendInvitations,
  restoreMembership,
  revokeMembership,
  type Membership,
} from "@/domains/assess/team/api";
import {
  ASSIGNABLE_ROLES,
  ROLE_DESCRIPTIONS,
  isActive,
  isOwner,
  roleLabel,
  staffCountLabel,
} from "@/domains/assess/team/support";

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
 *
 * The list is one server page at a time, searched in SQL, rather than the
 * whole team walked and filtered in the browser. The panel owns its own load
 * and re-fetches on mutation, so `Team` no longer needs to hold the list just
 * to hand it down.
 */
export function MembersPanel({
  orgSlug,
  canManage,
}: {
  orgSlug: string;
  canManage: boolean;
}) {
  const [pending, setPending] = useState<Pending>(null);
  const [role, setRole] = useState<string>("supervisor");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [resendingId, setResendingId] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  // What the server is asked for: the box, once typing pauses.
  const query = useSearchQuery(search);

  // A page at a time, searched in SQL, rather than the whole team walked and
  // filtered in the browser.
  const pages = useCursorPages(
    (cursor, signal) => listMemberships(orgSlug, signal, { cursor, search: query }),
    [orgSlug, query],
  );
  const rows = pages.state.data ?? [];

  // Everybody on the loaded pages who has not yet chosen a password.
  const awaiting = rows.filter((member) => member.invited && isActive(member) && !isOwner(member));
  const [resendingAll, setResendingAll] = useState(false);

  async function resendAll() {
    setError(null);
    setResendingAll(true);
    try {
      const { results } = await resendInvitations(orgSlug, awaiting.map((member) => member.id));
      const sent = results.filter((result) => result.outcome === "sent").length;
      setNotice(`Resent ${sent} of ${results.length} invitations.`);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setResendingAll(false);
    }
  }

  async function resend(member: Membership) {
    setError(null);
    setResendingId(member.id);
    try {
      const result = await resendInvitation(orgSlug, member.id);
      setNotice(`Resent the invitation to ${result.email}.`);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setResendingId(null);
    }
  }

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
      pages.state.reload();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  const columns = useMemo(
    () => [
      {
        header: "Email",
        key: "email" as keyof Membership,
        priority: "primary" as const,
        render: (member: Membership) => (
          <div className={b2cTableCellText}>
            <span className="font-medium text-osce-ink-900">
              {member.email ?? "No email address on file"}
            </span>
            {member.email ? null : (
              <span className="ml-2 font-mono text-osce-caption text-b2b-icon">
                {member.user_id.slice(0, 8)}
              </span>
            )}
            {member.invited ? (
              <span className="ml-2 text-osce-caption text-b2b-mid">Invited</span>
            ) : null}
          </div>
        ),
      },
      {
        header: "Role",
        key: "role" as keyof Membership,
        render: (member: Membership) => (
          <span className={cn(b2cTableCellText, "text-b2b-graphite")}>{roleLabel(member.role)}</span>
        ),
      },
      {
        header: "Circuits led",
        key: "circuits_led" as keyof Membership,
        render: (member: Membership) => (
          <span className={cn(b2cTableCellText, "tabular-nums text-b2b-graphite")}>
            {member.circuits_led}
          </span>
        ),
      },
      {
        header: "Access",
        key: "id" as keyof Membership,
        render: (member: Membership) =>
          isActive(member) ? (
            <Badge variant="success" dot>Active</Badge>
          ) : (
            <Badge variant="warning" dot>Revoked</Badge>
          ),
      },
      {
        header: "Actions",
        key: "user_id" as keyof Membership,
        priority: "detail" as const,
        render: (member: Membership) =>
          canManage ? (
            <RowActions
              member={member}
              onAction={open}
              onResend={resend}
              resending={resendingId === member.id}
            />
          ) : null,
      },
    ],
    [canManage, resendingId],
  );

  return (
    <div className="min-w-0 space-y-4">
      {notice ? <Alert tone="success">{notice}</Alert> : null}
      {/* A dialog shows its own error; a resend has no dialog to show it in. */}
      {error && !pending ? <Alert tone="danger">{error}</Alert> : null}

      <PlatformFilterBar
        leading={
          rows.length > 0 || query ? (
            <p className={b2bTokens.b2bEyebrow}>
              {staffCountLabel(rows.length)}
              {pages.hasMore ? "+" : ""}
            </p>
          ) : null
        }
      >
        <PlatformFilterSearch
          value={search}
          onChange={setSearch}
          placeholder="Search staff…"
          aria-label="Search staff"
        />
        {canManage && awaiting.length > 0 ? (
          <Button
            themeType="b2b"
            variant="secondary"
            size="sm"
            disabled={resendingAll}
            onClick={() => resendAll()}
          >
            {resendingAll ? "Resending…" : `Resend invitations (${awaiting.length})`}
          </Button>
        ) : null}
      </PlatformFilterBar>

      {pages.state.error ? (
        <Alert tone="danger">
          {pages.state.error.message}
          <button type="button" className="ml-2 underline" onClick={() => pages.state.reload()}>
            Retry
          </button>
        </Alert>
      ) : null}

      {pages.state.loading && !pages.state.data ? (
        <p className="text-osce-body text-b2c-text-secondary" role="status">
          Loading staff…
        </p>
      ) : rows.length === 0 ? (
        query ? (
          <p className="text-osce-body text-b2b-mid">No staff match &ldquo;{query}&rdquo;.</p>
        ) : (
          <EmptyState
            title="No staff yet"
            description="Invite a supervisor so somebody can run a circuit."
          />
        )
      ) : (
        <Table<Membership>
          rows={rows}
          more={pages}
          themeType="b2b"
          columns={columns}
          idField="id"
        />
      )}

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
  onAction,
  onResend,
  resending,
}: {
  member: Membership;
  onAction: (pending: NonNullable<Pending>) => void;
  onResend: (member: Membership) => void;
  resending: boolean;
}) {
  const owner = isOwner(member);
  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      {!owner && isActive(member) && member.invited ? (
        <Button
          themeType="b2b"
          variant="secondary"
          size="sm"
          disabled={resending}
          title="Only sent if that person has not set up their account yet."
          onClick={() => onResend(member)}
        >
          {resending ? "Resending…" : "Resend invitation"}
        </Button>
      ) : null}
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
          disabled={owner}
          // Whether this is the last administrator is the server's call (409
          // `last_admin`), shown in the dialog: a count of the loaded page
          // was wrong whenever the team ran past one page.
          title={owner ? "An organisation's owner cannot be revoked here" : undefined}
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
