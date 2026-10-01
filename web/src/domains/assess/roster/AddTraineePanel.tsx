"use client";

import { useCallback, useState } from "react";
import { HiOutlineArrowUpTray, HiOutlineUserPlus, HiOutlineUsers } from "react-icons/hi2";
import { Alert, Button, b2bTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { PanelCard } from "@/domains/assess/team/chrome";
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
 * The old form also took a password, generated one, showed it and offered to
 * email it. The platform invites an unknown address instead — the account is
 * created and the person is emailed a link to choose their own password — so
 * the form is a name, an address and a group.
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
  const [importOpen, setImportOpen] = useState(false);

  const submit = useCallback(async () => {
    const address = email.trim();
    if (!address) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const { firstName, lastName } = splitName(name);
      const trainee = await addTrainee(orgSlug, {
        email: address,
        firstName,
        lastName,
        cohortId: cohortId || null,
      });
      setNotice(`${trainee.email} is on the roster.`);
      setName("");
      setEmail("");
      onAdded();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [name, email, cohortId, orgSlug, onAdded]);

  if (!canManage) {
    return (
      <Alert tone="info" title="Only an owner or admin can add trainees">
        Ask one of them to add the people you need on the roster.
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      <PanelCard
        title="Add one person"
        subtitle="They are invited by email. If they have no account yet, we create one and send them a link to choose a password."
        icon={<HiOutlineUsers className="h-5 w-5" aria-hidden />}
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

          {error ? <Alert tone="danger">{error}</Alert> : null}
          {notice ? <Alert tone="success">{notice}</Alert> : null}

          <Button
            type="submit"
            themeType="b2b"
            variant="commit"
            disabled={busy || email.trim().length === 0}
            className="inline-flex items-center gap-2"
          >
            <HiOutlineUserPlus className="h-4 w-4 shrink-0" aria-hidden />
            {busy ? "Saving…" : "Add trainee"}
          </Button>
        </form>
      </PanelCard>

      <PanelCard
        title="Import a spreadsheet"
        subtitle="Upload a list of trainees saved from Excel or Google Sheets as a .csv file. Anyone already on the list is skipped and shown to you."
        icon={<HiOutlineArrowUpTray className="h-5 w-5" aria-hidden />}
      >
        <Button themeType="b2b" variant="secondary" onClick={() => setImportOpen(true)}>
          Import from spreadsheet
        </Button>
      </PanelCard>

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
