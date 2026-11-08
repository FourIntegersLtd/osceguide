"use client";

import { say } from "@/domains/assess/roster/rosterWords";
import { useAssessWords } from "@/capabilities/assess-words";
import { useCallback, useState } from "react";
import { hasCode } from "@/foundation/platform-client";
import { errorMessage } from "@/foundation/hooks";
import { PeopleDialog as Dialog } from "@/domains/assess/ui";
import { deleteGroup, renameGroup, type TraineeGroup } from "@/domains/assess/roster/api";
import { boardInput, boardLabel as fieldLabel } from "@/foundation/ui/boardKit";

/**
 * The two things a group row can be corrected into: renamed, or removed.
 *
 * Both live together because both are about the row rather than the people in
 * it, and both are reached from the same place on the Groups card.
 */

/**
 * Rename a group. Its members stay.
 *
 * The wording matters: the retiring client renamed a copied label and offered a
 * flag to rewrite the copies, so a rename looked like it had emptied the group.
 * This route rewrites one row that every membership points at, which is what
 * the sentence below promises.
 */
export function RenameGroupDialog({
  orgSlug,
  group,
  onClose,
  onSaved,
}: {
  orgSlug: string;
  group: TraineeGroup | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  if (!group) return null;
  // Keyed so opening a second group starts from that row's own label.
  return (
    <RenameForm
      key={group.id}
      orgSlug={orgSlug}
      groupId={group.id}
      initial={group.label}
      onClose={onClose}
      onSaved={onSaved}
    />
  );
}

function RenameForm({
  orgSlug,
  groupId,
  initial,
  onClose,
  onSaved,
}: {
  orgSlug: string;
  groupId: string;
  initial: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [label, setLabel] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const commit = useCallback(async () => {
    const name = label.trim();
    if (!name) return;
    setBusy(true);
    setError(null);
    try {
      await renameGroup(orgSlug, groupId, name);
      onSaved();
      onClose();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [orgSlug, groupId, label, onSaved, onClose]);

  return (
    <Dialog
      open
      title="Rename group"
      lead={`Everyone still in “${initial}” stays in it. Only the name changes.`}
      error={error}
      busy={busy}
      commitLabel="Rename"
      busyLabel="Saving…"
      commitDisabled={label.trim() === ""}
      onClose={onClose}
      onCommit={() => void commit()}
    >
      <div>
        <label htmlFor="assess-rename-group" className={fieldLabel}>
          New name
        </label>
        <input
          id="assess-rename-group"
          value={label}
          onChange={(event) => setLabel(event.target.value)}
          className={boardInput}
          autoComplete="off"
        />
      </div>
    </Dialog>
  );
}

/**
 * Delete a group.
 *
 * The backend refuses while anybody is in it (`group_not_empty`) rather than
 * quietly dropping the membership and everything addressed to the group, so the
 * refusal is shown in the dialog instead of the dialog closing on a half-truth.
 * The count is on screen because it is the thing to act on: empty it from
 * People, then delete.
 */
export function DeleteGroupDialog({
  orgSlug,
  group,
  onClose,
  onDeleted,
}: {
  orgSlug: string;
  group: TraineeGroup | null;
  onClose: () => void;
  onDeleted: () => void;
}) {
  if (!group) return null;
  return (
    <DeleteForm
      key={group.id}
      orgSlug={orgSlug}
      group={group}
      onClose={onClose}
      onDeleted={onDeleted}
    />
  );
}

function DeleteForm({
  orgSlug,
  group,
  onClose,
  onDeleted,
}: {
  orgSlug: string;
  group: TraineeGroup;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const w = useAssessWords();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const commit = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await deleteGroup(orgSlug, group.id);
      onDeleted();
      onClose();
    } catch (cause) {
      /* Branch on the code and keep the backend's sentence. The count on screen
         was read when the list loaded, so it can be stale — somebody else may
         have filled the group since, and this answer is the live one. */
      setError(
        hasCode(cause, "group_not_empty")
          ? `${errorMessage(cause)} Open ${w.People}, untick everybody and save, then delete it.`
          : errorMessage(cause),
      );
    } finally {
      setBusy(false);
    }
  }, [orgSlug, group.id, onDeleted, onClose]);

  const people = `${group.member_count} ${say(w, group.member_count === 1 ? "person" : "people")}`;

  return (
    <Dialog
      open
      tone="danger"
      title="Delete group?"
      lead={
        group.member_count === 0
          ? `Delete “${group.label}”? It has nobody in it, so nothing else changes. This cannot be undone.`
          : `Delete “${group.label}”? It still has ${people} in it, and a group is not deleted while it does. Empty it from ${w.People} first.`
      }
      error={error}
      busy={busy}
      commitLabel="Delete group"
      busyLabel="Deleting…"
      commitDisabled={group.member_count > 0}
      onClose={onClose}
      onCommit={() => void commit()}
    />
  );
}
