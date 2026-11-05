"use client";

import { useCallback, useState } from "react";
import { Alert, b2bTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { Dialog } from "@/domains/assess/team/chrome";
import type { Trainee } from "@/domains/assess/api";
import { updateTrainee, type Cohort } from "@/domains/assess/roster/api";

/**
 * Correct a roster entry — the old `TraineeMembersEditModal`.
 *
 * The address is shown and not editable, which is what the old modal did and
 * what this backend enforces: the address identifies the entry inside the
 * organisation and is what the account link was made against, so editing it is
 * not fixing a typo but re-pointing a person's results.
 *
 * The old modal's group picker offered a free-text "other label", because
 * there a cohort was a string copied onto every trainee. Here it is a cohort
 * row with an id, so the form offers the rows that exist and a blank one.
 * Which groups a person belongs to is not on this form at all — that is a
 * membership row, saved by `GroupMembersDialog`.
 */
export function TraineeEditDialog({
  orgSlug,
  trainee,
  cohorts,
  onClose,
  onSaved,
}: {
  orgSlug: string;
  trainee: Trainee | null;
  cohorts: Cohort[];
  onClose: () => void;
  onSaved: () => void;
}) {
  if (!trainee) return null;
  // Keyed so opening a second row starts from that row's own values rather
  // than the last one's — the same trick `GroupMembersDialog` uses.
  return (
    <Form
      key={trainee.id}
      orgSlug={orgSlug}
      trainee={trainee}
      cohorts={cohorts}
      onClose={onClose}
      onSaved={onSaved}
    />
  );
}

function Form({
  orgSlug,
  trainee,
  cohorts,
  onClose,
  onSaved,
}: {
  orgSlug: string;
  trainee: Trainee;
  cohorts: Cohort[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [firstName, setFirstName] = useState(trainee.first_name ?? "");
  const [lastName, setLastName] = useState(trainee.last_name ?? "");
  const [cohortId, setCohortId] = useState(trainee.cohort_id ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const commit = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      // All three are sent because all three are on screen; a blank name is a
      // deliberate clear, which is why they go as `null` and not `undefined`.
      await updateTrainee(orgSlug, trainee.id, {
        firstName: firstName.trim() || null,
        lastName: lastName.trim() || null,
        cohortId: cohortId || null,
      }, trainee.revision);
      onSaved();
      onClose();
    } catch (cause) {
      setError(
        hasCode(cause, "stale_revision")
          ? "Someone else changed this person just now. We have reloaded the list: close this and choose Edit again to see their changes."
          : errorMessage(cause),
      );
      if (hasCode(cause, "stale_revision")) onSaved();
    } finally {
      setBusy(false);
    }
  }, [orgSlug, trainee.id, trainee.revision, firstName, lastName, cohortId, onSaved, onClose]);

  return (
    <Dialog
      open
      title="Edit trainee"
      lead="Only what is on this form is written. The email address cannot be changed here, because it keeps this person’s results linked to them."
      error={error}
      busy={busy}
      commitLabel="Save"
      busyLabel="Saving…"
      onClose={onClose}
      onCommit={() => void commit()}
    >
      <div>
        <p className="text-osce-caption font-semibold text-b2b-mid">Member</p>
        <p className="mt-1 text-osce-body font-medium text-b2b-headline">{trainee.email}</p>
      </div>

      <div className="grid grid-cols-1 gap-3 rounded-panel border border-b2b-border bg-b2b-cream/60 p-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="assess-trainee-edit-first"
            className="block text-osce-caption font-medium text-b2b-graphite"
          >
            First name
          </label>
          <input
            id="assess-trainee-edit-first"
            value={firstName}
            onChange={(event) => setFirstName(event.target.value)}
            className={`mt-1 ${b2bTokens.b2bInputBase}`}
            autoComplete="off"
          />
        </div>
        <div>
          <label
            htmlFor="assess-trainee-edit-last"
            className="block text-osce-caption font-medium text-b2b-graphite"
          >
            Last name
          </label>
          <input
            id="assess-trainee-edit-last"
            value={lastName}
            onChange={(event) => setLastName(event.target.value)}
            className={`mt-1 ${b2bTokens.b2bInputBase}`}
            autoComplete="off"
          />
        </div>
      </div>

      <div>
        <label
          htmlFor="assess-trainee-edit-cohort"
          className="block text-osce-caption font-medium text-b2b-graphite"
        >
          Cohort
        </label>
        <p className="mt-0.5 text-osce-caption text-b2b-mid">
          An intake. Choose an existing one; year groups are created under Groups and year groups.
        </p>
        <select
          id="assess-trainee-edit-cohort"
          value={cohortId}
          onChange={(event) => setCohortId(event.target.value)}
          className={`mt-1 ${b2bTokens.b2bInputBase}`}
        >
          <option value="">No year group</option>
          {cohorts.map((cohort) => (
            <option key={cohort.id} value={cohort.id}>
              {cohort.name}
            </option>
          ))}
        </select>
        {cohorts.length === 0 ? (
          <Alert tone="info" className="mt-2">
            No cohorts in the organisation yet. Create one under Groups, then
            come back to set it here.
          </Alert>
        ) : null}
      </div>
    </Dialog>
  );
}
