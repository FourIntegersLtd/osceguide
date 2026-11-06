"use client";

import { roleLabel } from "@/foundation/session/roles";
import { useSession } from "@/foundation/session";
import { useState } from "react";
import { b2bTokens as t, cn } from "@/foundation/ui";
import { Chip, Note, card, h2, hint, row, th, PeopleDialog as Dialog } from "@/domains/assess/ui";
import { errorMessage, useCursorPages, useSearchQuery } from "@/foundation/hooks";
import {
  changeMemberRole,
  listMemberships,
  resendInvitation,
  resendInvitations,
  restoreMembership,
  revokeMembership,
  revokeMemberships,
  type Membership,
} from "@/domains/assess/team/api";
import {
  ASSIGNABLE_ROLES,
  ROLE_CHOICE_HELP,
  bulkRevokeFailure,
  isActive,
  isAwaitingInvite,
  isOwner,
  resendSummary,
  revokableStaff,
  staffCountLabel,
  revokeLead,
  staffRevokeTitle,
} from "@/domains/assess/team/support";
import { boardBtn, boardPadWide, boardInput, boardLabel, boardButtonSmall } from "@/foundation/ui/boardKit";

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
  onInviteStaff,
}: {
  orgSlug: string;
  canManage: boolean;
  /** Opens the Add people sheet on Staff, from the empty state. */
  onInviteStaff: () => void;
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
  const awaiting = rows.filter(isAwaitingInvite);
  const [resendingAll, setResendingAll] = useState(false);

  // Ticked rows (membership ids). Only rows still on the loaded pages ever reach a call.
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [confirmingBulk, setConfirmingBulk] = useState(false);
  const selectedRows = rows.filter((member) => selected.has(member.id));
  const { session } = useSession();
  const selfId = session?.user.id;
  const revokable = revokableStaff(selectedRows, rows, selfId);
  const toggle = (id: string) =>
    setSelected((current) => {
      const next = new Set(current);
      if (!next.delete(id)) next.add(id);
      return next;
    });

  async function revokeSelected() {
    setBusy(true);
    setError(null);
    try {
      const { results } = await revokeMemberships(
        orgSlug,
        revokable.map((member) => member.id),
      );
      const done = results.filter((result) => result.outcome === "revoked").length;
      setNotice(`Revoked access for ${done} of ${results.length} staff.`);
      setSelected(new Set());
      setConfirmingBulk(false);
      pages.state.reload();
    } catch (cause) {
      setError(bulkRevokeFailure(cause, errorMessage(cause)));
      pages.state.reload();
    } finally {
      setBusy(false);
    }
  }

  /** Resend the choose-a-password link to these people and say how many went. */
  async function resendTo(members: Membership[]) {
    setError(null);
    setResendingAll(true);
    try {
      const { results } = await resendInvitations(
        orgSlug,
        members.map((member) => member.id),
      );
      setNotice(resendSummary(results));
      return true;
    } catch (cause) {
      setError(errorMessage(cause));
      return false;
    } finally {
      setResendingAll(false);
    }
  }
  const resendSelected = async () => {
    if (await resendTo(selectedRows.filter(isAwaitingInvite))) setSelected(new Set());
  };
  const resendAll = () => resendTo(awaiting);

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
        setNotice(`${who} is now ${roleLabel(role)}.`);
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

  return (
    <div className="flex min-w-0 flex-col gap-6">
      {notice ? <Note tone="ok">{notice}</Note> : null}
      {/* A dialog shows its own error; a resend has no dialog to show it in. */}
      {error && !pending ? <Note tone="bad" role="alert">{error}</Note> : null}

      <div className="flex flex-wrap items-center gap-3">
        {rows.length > 0 || query ? (
          <span className={t.assessEyebrow}>
            {staffCountLabel(rows.length)}
            {pages.hasMore ? "+" : ""}
          </span>
        ) : null}
        <input
          className={cn(boardInput, "flex-[1_1_260px] !w-auto")}
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search staff…"
          aria-label="Search staff"
        />
        {canManage && awaiting.length > 0 ? (
          <button type="button" className={boardBtn()} disabled={resendingAll} onClick={() => resendAll()}>
            {resendingAll ? "Resending…" : `Resend invitations (${awaiting.length})`}
          </button>
        ) : null}
      </div>

      {canManage && selectedRows.length > 0 ? (
        <div className={cn(card, "border-assess-chip-info-bg")}>
          <div className={cn(row, "gap-2 border-t-0")}>
            <b className="font-semibold">{selectedRows.length} selected</b>
            <button type="button" className={boardButtonSmall} disabled={resendingAll || busy} onClick={() => void resendSelected()}>
              Resend invitation
            </button>
            <button
              type="button"
              className={boardBtn("danger", true)}
              disabled={busy || revokable.length === 0}
              onClick={() => {
                setError(null);
                setConfirmingBulk(true);
              }}
            >
              Revoke access
            </button>
            <button type="button" className="text-assess-label text-osce-accent hover:text-osce-accent-hover" onClick={() => setSelected(new Set())}>
              Clear
            </button>
          </div>
        </div>
      ) : null}

      {pages.state.error ? (
        <div className={boardPadWide}>
          <Note tone="bad" role="alert">
            {pages.state.error.message}{" "}
            <button type="button" className="text-osce-accent hover:text-osce-accent-hover" onClick={() => pages.state.reload()}>
              Retry
            </button>
          </Note>
        </div>
      ) : null}

      {pages.state.loading && !pages.state.data ? (
        <p className="text-osce-body text-osce-ink-500" role="status">
          Loading staff…
        </p>
      ) : rows.length === 0 ? (
        pages.state.error ? null : query ? (
          <div className={boardPadWide}>
            <div className={t.assessMeta}>Search with no match</div>
            <div>No staff match &ldquo;{query}&rdquo;.</div>
          </div>
        ) : (
          <div className={boardPadWide}>
            <h2 className={h2}>No staff yet</h2>
            <p className={cn(t.assessMeta, "m-0")}>Invite a supervisor so somebody can run a circuit.</p>
            {canManage ? (
              <button type="button" className={cn(boardBtn("primary"), "self-start")} onClick={onInviteStaff}>
                Invite staff
              </button>
            ) : null}
          </div>
        )
      ) : (
        <div role="table" className={card}>
          <div role="row" className={th}>
            {canManage ? <span className="w-4" /> : null}
            <span className="flex-[1_1_220px]">Email</span>
            <span className="w-[100px]">Role</span>
            <span className="w-[90px]">Circuits led</span>
            <span className="w-[90px]">Access</span>
            {canManage ? <span>Actions</span> : null}
          </div>
          {rows.map((member) => (
            <div key={member.id} role="row" data-testid="staff-row" className={row}>
              {canManage ? (
                <input
                  type="checkbox"
                  aria-label={`Select ${member.email ?? "this person"}`}
                  checked={selected.has(member.id)}
                  disabled={isOwner(member) || !isActive(member)}
                  onChange={() => toggle(member.id)}
                />
              ) : null}
              <span className="flex-[1_1_220px]">
                {member.email ?? "No email address on file"}{" "}
                {member.email ? null : <span className="font-mono text-assess-chip text-osce-ink-500">{member.user_id.slice(0, 8)}</span>}
                {member.invited ? <Chip>Invited</Chip> : null}
              </span>
              <span className="w-[100px]">{roleLabel(member.role)}</span>
              <span className="w-[90px] tabular-nums">{member.circuits_led}</span>
              <span className="w-[90px]">
                <Chip tone={isActive(member) ? "ok" : "warn"}>{isActive(member) ? "● Active" : "● Revoked"}</Chip>
              </span>
              {canManage ? (
                <RowActions member={member} onAction={open} onResend={resend} resending={resendingId === member.id} />
              ) : null}
            </div>
          ))}
          {pages.hasMore || pages.moreError ? (
            <div className={cn(row, "justify-center")}>
              <button type="button" className={boardButtonSmall} disabled={pages.loadingMore} onClick={pages.loadMore}>
                {pages.loadingMore ? "Loading…" : "Load more"}
              </button>
              {pages.moreError ? <span className="text-osce-danger-text">{pages.moreError.message}</span> : null}
            </div>
          ) : null}
        </div>
      )}

      {!canManage ? (
        <div className={boardPadWide}>
          <div className={t.assessMeta}>Supervisor (read only)</div>
          <div>Contact an owner or admin to change who has access.</div>
        </div>
      ) : null}

      <Dialog
        open={confirmingBulk}
        title={staffRevokeTitle(revokable.length)}
        lead="They lose access to this organisation. Nothing they have marked is deleted. The owner, you and the last admin are left out of the selection; if a revoke would still leave no admin, nobody is revoked."
        error={error}
        busy={busy}
        tone="danger"
        commitLabel="Revoke access"
        busyLabel="Revoking…"
        onClose={() => setConfirmingBulk(false)}
        onCommit={() => void revokeSelected()}
      />

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
          <label htmlFor="assess-member-role" className={boardLabel}>
            Their role
          </label>
          <select
            id="assess-member-role"
            value={role}
            onChange={(event) => setRole(event.target.value)}
            className={boardInput}
          >
            {ASSIGNABLE_ROLES.map((value) => (
              <option key={value} value={value}>
                {roleLabel(value)}
              </option>
            ))}
          </select>
          <p className={hint}>{ROLE_CHOICE_HELP}</p>
        </div>
      </Dialog>

      <Dialog
        open={pending?.kind === "revoke"}
        title="Revoke access"
        lead={
          pending
            ? revokeLead(pending.member.email, pending.member.user_id === selfId)
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
    <div className="flex flex-wrap items-center gap-2.5">
      {!owner && isActive(member) && member.invited ? (
        <button
          type="button"
          className={boardButtonSmall}
          disabled={resending}
          title="Only sent if that person has not set up their account yet."
          onClick={() => onResend(member)}
        >
          {resending ? "Resending…" : "Resend invitation"}
        </button>
      ) : null}
      {!owner ? (
        <button type="button" className={boardButtonSmall} onClick={() => onAction({ kind: "role", member })}>
          Change role
        </button>
      ) : null}
      {isActive(member) ? (
        <button
          type="button"
          className={boardButtonSmall}
          disabled={owner}
          // Whether this is the last administrator is the server's call (409
          // `last_admin`), shown in the dialog: a count of the loaded page
          // was wrong whenever the team ran past one page.
          title={owner ? "An organisation's owner cannot be revoked here" : undefined}
          onClick={() => onAction({ kind: "revoke", member })}
        >
          Revoke
        </button>
      ) : (
        <button type="button" className={boardButtonSmall} onClick={() => onAction({ kind: "restore", member })}>
          Restore
        </button>
      )}
    </div>
  );
}
