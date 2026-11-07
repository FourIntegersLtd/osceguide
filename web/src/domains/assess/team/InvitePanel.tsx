"use client";

import { useState } from "react";
import { b2bTokens as t, cn } from "@/foundation/ui";
import { Note, PasswordFields, h2, hint } from "@/domains/assess/ui";
import { IssuedPassword } from "@/foundation/ui/TemporaryPassword";
import { useTemporaryPassword } from "@/foundation/ui/useTemporaryPassword";
import { errorMessage } from "@/foundation/hooks";
import { inviteMember, type SeatedMembership } from "@/domains/assess/team/api";
import { BulkInviteDialog } from "@/domains/assess/team/BulkInviteDialog";
import {
  ASSIGNABLE_ROLES,
  type AssignableRole,
  roleDescription,
  teamRoleLabel,
} from "@/domains/assess/team/support";
import { boardBtn, boardPadWide, boardInput, boardLabel } from "@/foundation/ui/boardKit";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * Add a member of staff.
 *
 * The platform invites: an address with no account gets one and a link to
 * choose a password, and the response says which happened. Where that email
 * cannot be delivered, the admin may instead type a temporary password for a
 * brand-new account and relay it by hand (the server applies it only to a new
 * account; it must be changed at first sign-in). Nothing is ever emailed in
 * plain text.
 *
 * The spreadsheet below it is the same act done to a list. The retiring client
 * had a staff upload that wrote a team row by row and generated a password per
 * person; here the browser parses the sheet, one request posts the rows, and an
 * address already on the team is reported rather than fatal — which is what
 * makes re-running last month's file harmless.
 */
export function InvitePanel({
  orgSlug,
  canManage,
  onInvited,
}: {
  orgSlug: string;
  canManage: boolean;
  onInvited: () => void;
}) {
  const w = useAssessWords();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<AssignableRole>("supervisor");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SeatedMembership | null>(null);
  const password = useTemporaryPassword();
  const [importOpen, setImportOpen] = useState(false);

  const submit = async () => {
    const address = email.trim();
    if (!address) return;
    setBusy(true);
    setError(null);
    setResult(null);
    password.dismiss();
    try {
      const membership = await inviteMember(orgSlug, {
        email: address,
        role,
        ...(password.typed ? { temporaryPassword: password.typed } : {}),
      });
      setResult(membership);
      password.finish(address, membership.temporary_password_applied === true);
      setEmail("");
      onInvited();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  if (!canManage) {
    return (
      <Note tone="info">
        <b className="block">Only an owner or admin can invite staff</b>
        Ask one of them to add the person you need.
      </Note>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <form
        className={boardPadWide}
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <h2 className={h2}>Invite someone to the team</h2>
        <p className={cn(t.assessMeta, "m-0")}>{`${w.Supervisors} run ${w.circuits} and mark them. Admins also manage the team and sign off results.`}</p>
        <div>
          <label htmlFor="assess-invite-email" className={boardLabel}>Email address</label>
          <input id="assess-invite-email" type="email" required autoComplete="off" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="supervisor@hospital.nhs.uk" className={boardInput} />
          <div className={hint}>If they have no account yet we create one and email them a link to choose a password.</div>
        </div>
        <div>
          <label htmlFor="assess-invite-role" className={boardLabel}>Their role</label>
          <select id="assess-invite-role" value={role} onChange={(event) => setRole(event.target.value as AssignableRole)} className={boardInput}>
            {ASSIGNABLE_ROLES.map((value) => (
              <option key={value} value={value}>
                {teamRoleLabel(value, w)}
              </option>
            ))}
          </select>
          <div className={hint}>{roleDescription(role, w)}</div>
        </div>

        <PasswordFields {...password.field} id="assess-invite-password" disabled={busy} />

        {error ? <Note tone="bad" role="alert">{error}</Note> : null}
        <button type="submit" className={cn(boardBtn("primary"), "self-start")} disabled={busy || email.trim().length === 0 || !password.ready}>
          {busy ? "Inviting…" : "+ Add person"}
        </button>
      </form>

      {password.issued ? (
        <IssuedPassword email={password.issued.email} password={password.issued.password} onDismiss={password.dismiss} />
      ) : result ? (
        <Note tone="ok">
          {result.invited
            ? `Invited ${result.email}. They have been emailed a link to choose a password.`
            : `${result.email} already had an account and is now ${teamRoleLabel(result.role, w).toLowerCase()} here.`}
        </Note>
      ) : null}

      <div className={boardPadWide}>
        <h2 className={h2}>Import a spreadsheet</h2>
        <p className={cn(t.assessMeta, "m-0")}>
          Upload a list of staff saved from Excel or Google Sheets as a .csv file. Anyone already on the team is skipped and shown to you.
        </p>
        <button type="button" className={cn(boardBtn(), "self-start")} onClick={() => setImportOpen(true)}>
          Import from spreadsheet
        </button>
      </div>

      <BulkInviteDialog
        orgSlug={orgSlug}
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={onInvited}
      />
    </div>
  );
}
