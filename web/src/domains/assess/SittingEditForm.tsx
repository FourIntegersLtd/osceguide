"use client";

import { useState } from "react";
import { Alert, AsyncBoundary, Input, Spinner } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { listProgrammes, updateSitting, type Sitting, type SittingMode } from "@/domains/assess/api";
import { ModeField, ProgrammeField, ScheduledForField } from "@/domains/assess/SittingFields";
import {
  fieldDateTime,
  hasChanges,
  programmeChoices,
  sittingChanges,
  sittingEditLock,
  sittingModeOf,
  type SittingFormValues,
} from "@/domains/assess/support";
import { Dialog } from "@/domains/assess/team/chrome";

/**
 * Correcting a sitting that has already been scheduled.
 *
 * The retiring client had a whole page for this (`OrgSessionEditPage`) with
 * three fields: a name, a type, and a feedback template. Those are still the
 * three questions — the template is answered here by the programme it is
 * resolved through, which is what the backend says the rubric comes from — and
 * the date is added because this backend keeps one and lets it move.
 *
 * It is a dialog on the sitting rather than a route, because it edits the thing
 * the screen is already showing and the screen has the answer to "what is
 * frozen" in the document it just loaded.
 *
 * Mounted only while open, so the fields always start from a freshly read
 * sitting rather than from whatever the last opening left behind.
 */
export function SittingEditForm({
  orgSlug,
  sitting,
  onClose,
  onSaved,
}: {
  orgSlug: string;
  sitting: Sitting;
  onClose: () => void;
  onSaved: () => void;
}) {
  const lock = sittingEditLock(sitting);
  const programmes = useAsync((signal) => listProgrammes(orgSlug, signal), [orgSlug]);
  const [values, setValues] = useState<SittingFormValues>({
    name: sitting.name,
    mode: sittingModeOf(sitting.mode),
    programmeId: sitting.programme_id ?? "",
    scheduledFor: fieldDateTime(sitting.scheduled_for),
  });
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const patch = sittingChanges(sitting, values);
  const set = <K extends keyof SittingFormValues>(key: K, value: SittingFormValues[K]) =>
    setValues((current) => ({ ...current, [key]: value }));

  async function commit() {
    setBusy(true);
    setFailure(null);
    try {
      await updateSitting(orgSlug, sitting.id, patch);
      onSaved();
      onClose();
    } catch (cause) {
      setFailure(refusal(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog
      open
      title="Edit this sitting"
      lead="Only what you change is written. The name and the date can move for the life of the record; what the sitting examines cannot once anybody has been examined against it."
      error={failure}
      busy={busy}
      commitLabel="Save sitting"
      busyLabel="Saving…"
      commitDisabled={busy || values.name.trim().length === 0 || !hasChanges(patch)}
      onClose={onClose}
      onCommit={() => void commit()}
    >
      <div className="flex flex-col gap-4">
        {lock.assessmentFrozen ? (
          <Alert tone="warning">
            A circuit on this sitting has started, so its mode and its programme are fixed — you can
            still rename it and move its date. To change what it examines, rebuild the circuits or
            schedule another sitting.
          </Alert>
        ) : lock.modeFrozen ? (
          <Alert tone="warning">
            This sitting already has {lock.circuits} circuit{lock.circuits === 1 ? "" : "s"}, so its
            mode is chosen for good — the mode is what those circuits are composed from.
          </Alert>
        ) : null}

        <Input
          label="Name"
          required
          value={values.name}
          onChange={(event) => set("name", event.target.value)}
        />

        <ModeField
          value={values.mode}
          onChange={(mode: SittingMode) => set("mode", mode)}
          disabled={lock.modeFrozen}
        />

        <AsyncBoundary state={programmes}>
          {(page) => (
            <ProgrammeField
              value={values.programmeId}
              onChange={(programmeId) => set("programmeId", programmeId)}
              programmes={programmeChoices(page.items, sitting.programme_id)}
              disabled={lock.assessmentFrozen}
            />
          )}
        </AsyncBoundary>

        {programmes.loading ? <Spinner label="Loading programmes" /> : null}

        <ScheduledForField
          value={values.scheduledFor}
          onChange={(scheduledFor) => set("scheduledFor", scheduledFor)}
          hint={
            sitting.scheduled_for
              ? "When it is due to run. Leave empty to unschedule it."
              : "Leave empty to schedule it later."
          }
        />
      </div>
    </Dialog>
  );
}

/**
 * The refusal, in the words this form can act on.
 *
 * Branching on `code` rather than on the server's English, per the house rule —
 * but keeping the server's sentence when the code is one this screen cannot
 * explain better, because its `invalid_circuit` message names what to do about
 * the circuits.
 */
function refusal(cause: unknown): string {
  if (hasCode(cause, "sitting_locked")) {
    return "This sitting has begun, so what it examines is fixed. Its name and date can still change.";
  }
  if (hasCode(cause, "exam_rubric_not_ready", "rubric_version_not_published")) {
    return "That programme has no published rubric to mark against yet. Publish one, or pick another programme.";
  }
  if (hasCode(cause, "programme_not_found")) {
    return "That programme is no longer here. Pick another.";
  }
  return errorMessage(cause);
}
