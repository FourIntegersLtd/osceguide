"use client";

import { useCallback, useState } from "react";
import { HiOutlineUserPlus } from "react-icons/hi2";
import { Alert, Button, b2bTokens, Panel } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { inviteMember, type Membership } from "@/domains/assess/team/api";
import { BulkInviteDialog } from "@/domains/assess/team/BulkInviteDialog";
import {
  ASSIGNABLE_ROLES,
  ROLE_DESCRIPTIONS,
  roleLabel,
  type AssignableRole,
} from "@/domains/assess/team/support";

/**
 * Add a member of staff.
 *
 * The old screen made a temporary password in the browser, showed it on the
 * page and asked an administrator to pass it on — with an "email their login"
 * button beside it that sent the password in plain text. The platform invites
 * instead: an address with no account gets one and a link to choose a
 * password, and the response says which happened. So this form is an address
 * and a role, and nothing here ever holds a credential.
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
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<AssignableRole>("supervisor");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Membership | null>(null);
  const [importOpen, setImportOpen] = useState(false);

  const submit = useCallback(async () => {
    const address = email.trim();
    if (!address) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const membership = await inviteMember(orgSlug, { email: address, role });
      setResult(membership);
      setEmail("");
      onInvited();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [email, role, orgSlug, onInvited]);

  if (!canManage) {
    return (
      <Alert tone="info" title="Only an owner or admin can invite staff">
        Ask one of them to add the person you need.
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <Panel
        title="Invite someone to the team"
        description="Supervisors run circuits and mark them. Admins also manage the team and sign off results."
      >
        <form
          className="space-y-5"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <div>
            <label
              htmlFor="assess-invite-email"
              className="block text-osce-body font-semibold text-b2b-headline"
            >
              Email address
            </label>
            <p className="mt-0.5 text-osce-caption text-b2b-mid">
              If they have no account yet we create one and email them a link to choose a password.
            </p>
            <input
              id="assess-invite-email"
              type="email"
              required
              autoComplete="off"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="supervisor@hospital.nhs.uk"
              className={`mt-2 ${b2bTokens.b2bInputBase}`}
            />
          </div>

          <div>
            <label
              htmlFor="assess-invite-role"
              className="block text-osce-body font-semibold text-b2b-headline"
            >
              Their role
            </label>
            <p className="mt-0.5 text-osce-caption text-b2b-mid">{ROLE_DESCRIPTIONS[role]}</p>
            <select
              id="assess-invite-role"
              value={role}
              onChange={(event) => setRole(event.target.value as AssignableRole)}
              className={`mt-2 ${b2bTokens.b2bInputBase}`}
            >
              {ASSIGNABLE_ROLES.map((value) => (
                <option key={value} value={value}>
                  {roleLabel(value)}
                </option>
              ))}
            </select>
          </div>

          {error ? <Alert tone="danger">{error}</Alert> : null}
          {result ? (
            <Alert tone="success">
              {result.invited
                ? `Invited ${result.email}. They have been emailed a link to choose a password.`
                : `${result.email} already had an account and is now ${roleLabel(result.role).toLowerCase()} here.`}
            </Alert>
          ) : null}

          <Button
            type="submit"
            themeType="b2b"
            variant="commit"
            disabled={busy || email.trim().length === 0}
            className="inline-flex items-center gap-2"
          >
            <HiOutlineUserPlus className="h-4 w-4 shrink-0" aria-hidden />
            {busy ? "Inviting…" : "Add person"}
          </Button>
        </form>
      </Panel>

      <Panel
        title="Import a spreadsheet"
        description="Upload a list of staff saved from Excel or Google Sheets as a .csv file. Anyone already on the team is skipped and shown to you."
      >
        <Button themeType="b2b" variant="secondary" onClick={() => setImportOpen(true)}>
          Import from spreadsheet
        </Button>
      </Panel>

      <BulkInviteDialog
        orgSlug={orgSlug}
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={onInvited}
      />
    </div>
  );
}
