"use client";

import { useState } from "react";
import { HiOutlineUserPlus } from "react-icons/hi2";
import { Alert, Button, b2bTokens, Panel } from "@/foundation/ui";
import { IssuedPassword, TemporaryPasswordField } from "@/foundation/ui/TemporaryPassword";
import { useTemporaryPassword } from "@/foundation/ui/useTemporaryPassword";
import { errorMessage } from "@/foundation/hooks";
import { addTrainee, type Cohort } from "@/domains/assess/roster/api";
import { BulkImportDialog } from "@/domains/assess/roster/BulkImportDialog";

/** "Amina Khan" → first "Amina", last "Khan"; one word is a first name. */
export function splitName(value: string): { firstName: string | null; lastName: string | null } {
  const parts = value.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { firstName: null, lastName: null };
  if (parts.length === 1) return { firstName: parts[0] ?? null, lastName: null };
  return {
    firstName: parts.slice(0, -1).join(" "),
    lastName: parts[parts.length - 1] ?? null,
  };
}

/**
 * Add trainees: one at a time, or a spreadsheet.
 *
 * The platform invites an unknown address — the account is created and the
 * person is emailed a link to choose their own password. Where that email cannot
 * be delivered, the admin may type a temporary password for a brand-new account
 * and relay it by hand (changed at first sign-in; never applied to an existing
 * account).
 */
export function AddTraineePanel({
  orgSlug,
  cohorts,
  canManage,
  onAdded,
}: {
  orgSlug: string;
  cohorts: Cohort[];
  canManage: boolean;
  onAdded: () => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [cohortId, setCohortId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const password = useTemporaryPassword();
  const [importOpen, setImportOpen] = useState(false);

  const submit = async () => {
    const address = email.trim();
    if (!address) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    password.dismiss();
    try {
      const { firstName, lastName } = splitName(name);
      const trainee = await addTrainee(orgSlug, {
        email: address,
        firstName,
        lastName,
        cohortId: cohortId || null,
        ...(password.typed ? { temporaryPassword: password.typed } : {}),
      });
      const applied = trainee.temporary_password_applied === true;
      setNotice(
        password.typed && !applied
          ? `${trainee.email} is on the roster. They already had an account, so the password you typed was not used.`
          : `${trainee.email} is on the roster.`,
      );
      password.finish(trainee.email, applied);
      setName("");
      setEmail("");
      onAdded();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  if (!canManage) {
    return (
      <Alert tone="info" title="Only an owner or admin can add trainees">
        Ask one of them to add the people you need on the roster.
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <Panel
        title="Add one person"
        description="They are invited by email. If they have no account yet, we create one and send them a link to choose a password. If that email cannot reach them, set a temporary password to relay by hand."
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
              htmlFor="assess-trainee-name"
              className="block text-osce-body font-semibold text-b2b-headline"
            >
              Full name
            </label>
            <input
              id="assess-trainee-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className={`mt-2 ${b2bTokens.b2bInputBase}`}
              placeholder="e.g. Amina Khan"
              autoComplete="off"
            />
          </div>

          <div>
            <label
              htmlFor="assess-trainee-email"
              className="block text-osce-body font-semibold text-b2b-headline"
            >
              Email address
            </label>
            <input
              id="assess-trainee-email"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className={`mt-2 ${b2bTokens.b2bInputBase}`}
              placeholder="amina@hospital.nhs.uk"
              autoComplete="off"
            />
          </div>

          <div>
            <label
              htmlFor="assess-trainee-cohort"
              className="block text-osce-body font-semibold text-b2b-headline"
            >
              Cohort (optional)
            </label>
            <p className="mt-0.5 text-osce-caption text-b2b-mid">
              An intake, such as &quot;June 2026&quot;. Cohorts are created under Groups.
            </p>
            <select
              id="assess-trainee-cohort"
              value={cohortId}
              onChange={(event) => setCohortId(event.target.value)}
              className={`mt-2 ${b2bTokens.b2bInputBase}`}
            >
              <option value="">No cohort</option>
              {cohorts.map((cohort) => (
                <option key={cohort.id} value={cohort.id}>
                  {cohort.name}
                </option>
              ))}
            </select>
          </div>

          <TemporaryPasswordField {...password.field} disabled={busy} />

          {error ? <Alert tone="danger">{error}</Alert> : null}
          {notice ? <Alert tone="success">{notice}</Alert> : null}
          {password.issued ? (
            <IssuedPassword
              email={password.issued.email}
              password={password.issued.password}
              onDismiss={password.dismiss}
            />
          ) : null}

          <Button
            type="submit"
            themeType="b2b"
            variant="commit"
            disabled={busy || email.trim().length === 0 || !password.ready}
            className="inline-flex items-center gap-2"
          >
            <HiOutlineUserPlus className="h-4 w-4 shrink-0" aria-hidden />
            {busy ? "Saving…" : "Add trainee"}
          </Button>
        </form>
      </Panel>

      <Panel
        title="Import a spreadsheet"
        description="Upload a list of trainees saved from Excel or Google Sheets as a .csv file. Anyone already on the list is skipped and shown to you."
      >
        <Button themeType="b2b" variant="secondary" onClick={() => setImportOpen(true)}>
          Import from spreadsheet
        </Button>
      </Panel>

      <BulkImportDialog
        orgSlug={orgSlug}
        open={importOpen}
        cohorts={cohorts}
        onClose={() => setImportOpen(false)}
        onImported={onAdded}
      />
    </div>
  );
}
