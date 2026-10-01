"use client";

import { useState } from "react";
import { hasCode } from "@/foundation/platform-client";
import { b2bTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { Dialog } from "@/domains/assess/team/chrome";
import { deleteCohort, renameCohort, type Cohort } from "@/domains/assess/roster/api";

/**
 * The two things a cohort row can be corrected into: renamed, or removed.
 *
 * A cohort rename is the case the retiring client could not do safely. It
 * rewrote a label copied onto every trainee, so a half-completed rename left
 * some people on the old name and some on the new; here it is one row and the
 * intake on each person is a pointer at it.
 */

export function RenameCohortDialog({
  orgSlug,
  cohort,
  onClose,
  onSaved,
}: {
  orgSlug: string;
  cohort: Cohort | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  if (!cohort) return null;
  // Keyed so opening a second cohort starts from that row's own values.
  return (
    <RenameForm
      key={cohort.id}
      orgSlug={orgSlug}
      cohort={cohort}
      onClose={onClose}
      onSaved={onSaved}
    />
  );
}

function RenameForm({
  orgSlug,
  cohort,
  onClose,
  onSaved,
}: {
  orgSlug: string;
  cohort: Cohort;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [name, setName] = useState(cohort.name);
  const [academicYear, setAcademicYear] = useState(cohort.academic_year ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const commit = async () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setBusy(true);
    setError(null);
    try {
      // Both fields are sent because both are on screen; a blank academic year
      // is therefore a deliberate clear, which the route honours.
      await renameCohort(orgSlug, cohort.id, {
        name: trimmed,
        academicYear: academicYear.trim() || null,
      });
      onSaved();
      onClose();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog
      open
      title="Rename cohort"
      lead="Everyone in this intake stays in it. Only the name changes."
      error={error}
      busy={busy}
      commitLabel="Save"
      busyLabel="Saving…"
      commitDisabled={name.trim() === ""}
      onClose={onClose}
      onCommit={() => void commit()}
    >
      <div>
        <label
          htmlFor="assess-rename-cohort-name"
          className="block text-osce-caption font-medium text-b2b-graphite"
        >
          New name
        </label>
        <input
          id="assess-rename-cohort-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          className={`mt-1 ${b2bTokens.b2bInputBase}`}
          autoComplete="off"
        />
      </div>
      <div>
        <label
          htmlFor="assess-rename-cohort-year"
          className="block text-osce-caption font-medium text-b2b-graphite"
        >
          Academic year
        </label>
        <p className="mt-0.5 text-osce-caption text-b2b-mid">
          Leave blank to take the year off this intake.
        </p>
        <input
          id="assess-rename-cohort-year"
          value={academicYear}
          onChange={(event) => setAcademicYear(event.target.value)}
          className={`mt-1 ${b2bTokens.b2bInputBase}`}
          placeholder="2026/27"
          autoComplete="off"
        />
      </div>
    </Dialog>
  );
}

/**
 * Remove an intake.
 *
 * Refused while trainees still belong to it (`cohort_in_use`): a silent clear
 * would leave those people looking as though they had never had an intake at
 * all. The refusal is shown here rather than swallowed, and the way round it is
 * on the Trainees tab — edit each person's cohort.
 */
export function DeleteCohortDialog({
  orgSlug,
  cohort,
  onClose,
  onDeleted,
}: {
  orgSlug: string;
  cohort: Cohort | null;
  onClose: () => void;
  onDeleted: () => void;
}) {
  if (!cohort) return null;
  return (
    <DeleteForm
      key={cohort.id}
      orgSlug={orgSlug}
      cohort={cohort}
      onClose={onClose}
      onDeleted={onDeleted}
    />
  );
}

function DeleteForm({
  orgSlug,
  cohort,
  onClose,
  onDeleted,
}: {
  orgSlug: string;
  cohort: Cohort;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const commit = async () => {
    setBusy(true);
    setError(null);
    try {
      await deleteCohort(orgSlug, cohort.id);
      onDeleted();
      onClose();
    } catch (cause) {
      /* Branch on the code and keep the backend's sentence. The roster count
         per cohort is not on this card at all, so the refusal is the only place
         an administrator learns which intake is still holding people. */
      setError(
        hasCode(cause, "cohort_in_use")
          ? `${errorMessage(cause)} Move them onto another intake from their row on the Trainees tab first.`
          : errorMessage(cause),
      );
    } finally {
      setBusy(false);
    }
  };

  const lead =
    `Delete “${cohort.name}”? Nobody can be put into it afterwards. This cannot be ` +
    "undone, and a cohort that still has trainees in it is not deleted.";

  return (
    <Dialog
      open
      tone="danger"
      title="Delete cohort"
      lead={lead}
      error={error}
      busy={busy}
      commitLabel="Delete cohort"
      busyLabel="Deleting…"
      onClose={onClose}
      onCommit={() => void commit()}
    />
  );
}
