"use client";

import { toggleInSet } from "@/domains/assess/support";
import { useState } from "react";
import { AsyncBoundary, b2bTokens as t, cn } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import type { Trainee } from "@/domains/assess/api";
import { readGroupMembers, setGroupMembers, type TraineeGroup } from "@/domains/assess/roster/api";
import { displayName, sortTrainees } from "@/domains/assess/roster/support";
import { Note, PeopleDialog, card, row } from "@/domains/assess/ui";

/**
 * Who is in a group.
 *
 * Reading membership is `GET …/members` and writing it is a PUT of the whole
 * list. The old client had neither: membership was a label copied onto
 * the trainee, so "add to group" wrote to the person, and two administrators
 * editing at once each kept half of the result.
 *
 * One dialog from open to close (the Modal must not remount when the list loads, or its Back marker
 * and focus trap restart); the body shows the loading state, then the picker.
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
  // The ticks the admin has made, tagged with their group so opening another starts from its own membership.
  const [edited, setEdited] = useState<{ groupId: string; ids: Set<string> } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!group) return null;
  const picked = edited?.groupId === group.id ? edited.ids : new Set(members.data ?? []);
  const toggle = (id: string) => setEdited({ groupId: group.id, ids: toggleInSet(picked, id) });

  // Closing forgets the ticks and any error, so reopening a group starts from its saved membership.
  const close = () => {
    setEdited(null);
    setError(null);
    onClose();
  };

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      // `trainees.id`: a group is a roster list, not a list of user accounts.
      await setGroupMembers(orgSlug, group.id, [...picked]);
      onSaved();
      close();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <PeopleDialog
      open
      title={`People in ${group.label}`}
      lead="Tick everyone who belongs to this group. Saving replaces the current list."
      error={error}
      busy={busy}
      commitLabel="Save group"
      busyLabel="Saving…"
      commitDisabled={!members.data || trainees.length === 0}
      onClose={close}
      onCommit={() => void save()}
    >
      <AsyncBoundary state={members}>
        {() =>
          trainees.length === 0 ? (
            <Note tone="info">Nobody is on the roster yet, so there is nobody to put in a group.</Note>
          ) : (
            <>
              <p className={cn(t.assessMeta, "m-0")}>
                {picked.size} of {trainees.length} selected.
              </p>
              <ul className={cn(card, "m-0 max-h-[220px] list-none overflow-auto p-0")}>
                {sortTrainees(trainees).map((trainee) => (
                  <li key={trainee.id}>
                    <label className={cn(row, "cursor-pointer")}>
                      <input type="checkbox" checked={picked.has(trainee.id)} onChange={() => toggle(trainee.id)} className="h-4 w-4 shrink-0" />
                      <span className="min-w-0 flex-1 truncate text-osce-ink-900">{displayName(trainee)}</span>
                      <span className={cn(t.assessMeta, "shrink-0")}>{trainee.email}</span>
                    </label>
                  </li>
                ))}
              </ul>
            </>
          )
        }
      </AsyncBoundary>
    </PeopleDialog>
  );
}
