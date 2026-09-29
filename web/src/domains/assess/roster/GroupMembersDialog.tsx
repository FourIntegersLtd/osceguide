"use client";

import { useCallback, useState } from "react";
import {
  Alert,
  AsyncBoundary,
  Modal,
  ModalCommitButton,
  ModalContent,
  ModalFooterActions,
  ModalSecondaryButton,
  ModalTitle,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import type { Trainee } from "@/domains/assess/api";
import { readGroupMembers, setGroupMembers, type TraineeGroup } from "@/domains/assess/roster/api";
import { displayName, sortTrainees } from "@/domains/assess/roster/support";

/**
 * Who is in a group.
 *
 * Reading membership is `GET …/members` and writing it is a PUT of the whole
 * list. The old client had neither: membership was a label copied onto
 * the trainee, so "add to group" wrote to the person, and two administrators
 * editing at once each kept half of the result.
 */
export function GroupMembersDialog({
  orgSlug,
  group,
  trainees,
  onClose,
  onSaved,
}: {
  orgSlug: string;
  group: TraineeGroup | null;
  trainees: Trainee[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const groupId = group?.id ?? null;
  const members = useAsync(
    async (signal) => (groupId ? readGroupMembers(orgSlug, groupId, signal) : null),
    [orgSlug, groupId],
  );

  if (!group) return null;

  return (
    <Modal onClose={onClose} title={`People in ${group.label}`} width="38rem">
      <ModalContent>
        <ModalTitle>People in {group.label}</ModalTitle>
        <p className="mt-1 text-osce-body text-b2b-mid">
          Tick everyone who belongs to this group. What you save replaces what is there.
        </p>
        <div className="mt-4">
          <AsyncBoundary state={members}>
            {(resolved) =>
              resolved ? (
                /* Keyed on the group so opening a different one starts from
                   its own membership rather than the previous group's. */
                <Picker
                  key={group.id}
                  orgSlug={orgSlug}
                  groupId={group.id}
                  trainees={trainees}
                  initial={resolved}
                  onClose={onClose}
                  onSaved={onSaved}
                />
              ) : null
            }
          </AsyncBoundary>
        </div>
      </ModalContent>
    </Modal>
  );
}

function Picker({
  orgSlug,
  groupId,
  trainees,
  initial,
  onClose,
  onSaved,
}: {
  orgSlug: string;
  groupId: string;
  trainees: Trainee[];
  initial: string[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [picked, setPicked] = useState<Set<string>>(() => new Set(initial));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = (id: string) =>
    setPicked((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const save = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      // `trainees.id`: a group is a roster list, not a list of user accounts.
      await setGroupMembers(orgSlug, groupId, [...picked]);
      onSaved();
      onClose();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [orgSlug, groupId, picked, onSaved, onClose]);

  if (trainees.length === 0) {
    return (
      <Alert tone="info">Nobody is on the roster yet, so there is nobody to put in a group.</Alert>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-osce-caption text-b2b-mid">
        {picked.size} of {trainees.length} selected.
      </p>
      <ul className="max-h-64 space-y-1 overflow-y-auto rounded-lg border border-b2b-border p-2">
        {sortTrainees(trainees).map((trainee) => (
          <li key={trainee.id}>
            <label className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-osce-body hover:bg-b2b-cream">
              <input
                type="checkbox"
                checked={picked.has(trainee.id)}
                onChange={() => toggle(trainee.id)}
                className="h-4 w-4 shrink-0"
              />
              <span className="min-w-0 truncate text-b2b-headline">{displayName(trainee)}</span>
              <span className="ml-auto shrink-0 text-osce-caption text-b2b-mid">
                {trainee.email}
              </span>
            </label>
          </li>
        ))}
      </ul>
      {error ? <Alert tone="danger">{error}</Alert> : null}
      <ModalFooterActions className="mt-2">
        <ModalSecondaryButton onClick={onClose} disabled={busy}>
          Cancel
        </ModalSecondaryButton>
        <ModalCommitButton onClick={() => void save()} disabled={busy}>
          {busy ? "Saving…" : "Save group"}
        </ModalCommitButton>
      </ModalFooterActions>
    </div>
  );
}
