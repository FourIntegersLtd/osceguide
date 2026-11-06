"use client";

import { useCallback, useState } from "react";
import { b2bTokens as t, cn } from "@/foundation/ui";
import { Fold, Note, card, h2, row } from "@/domains/assess/ui";
import { errorMessage } from "@/foundation/hooks";
import type { Trainee } from "@/domains/assess/api";
import { addTraineeGroup, type Cohort, type TraineeGroup } from "@/domains/assess/roster/api";
import { CohortsPanel } from "@/domains/assess/roster/CohortsPanel";
import { GroupMembersDialog } from "@/domains/assess/roster/GroupMembersDialog";
import {
  DeleteGroupDialog,
  RenameGroupDialog,
} from "@/domains/assess/roster/GroupEditDialogs";
import { boardBtn, boardPadWide, boardInput, boardButtonSmall } from "@/foundation/ui/boardKit";

type Pending =
  | { kind: "rename"; group: TraineeGroup }
  | { kind: "delete"; group: TraineeGroup }
  | null;

/**
 * Cohorts and groups, which the old client conflated into one free-text label.
 *
 * A cohort is an intake a trainee belongs to — one each, set when they are
 * added. A group is a list you put on a circuit, and somebody can be in
 * several. The old roster had a single `cohort` string doing both jobs, which
 * is why "move to group" rewrote a field on every selected person and a renamed
 * group orphaned everyone in it.
 *
 * The cohorts card is `CohortsPanel` and a group row's dialogs are
 * `GroupEditDialogs`; what is left here is the groups list, its create form and
 * the one error area they share.
 */
export function GroupsPanel({
  orgSlug,
  cohorts,
  groups,
  trainees,
  canManage,
  onChanged,
}: {
  orgSlug: string;
  cohorts: Cohort[];
  groups: TraineeGroup[];
  trainees: Trainee[];
  canManage: boolean;
  onChanged: () => void;
}) {
  const [groupLabel, setGroupLabel] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<TraineeGroup | null>(null);
  const [pending, setPending] = useState<Pending>(null);

  const createGroup = useCallback(async () => {
    const label = groupLabel.trim();
    if (!label) return;
    setBusy(true);
    setError(null);
    try {
      await addTraineeGroup(orgSlug, label);
      setGroupLabel("");
      onChanged();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [groupLabel, orgSlug, onChanged]);

  const open = (next: NonNullable<Pending>) => {
    setError(null);
    setPending(next);
  };

  return (
    <div className="grid grid-cols-1 items-stretch gap-4 min-[901px]:grid-cols-2">
      <CohortsPanel
        orgSlug={orgSlug}
        cohorts={cohorts}
        canManage={canManage}
        onChanged={onChanged}
      />

      <div className={boardPadWide}>
        <h2 className={h2}>Groups</h2>
        <p className={cn(t.assessMeta, "m-0")}>
          A named list of people you can add to a circuit together, such as a rotation team or a resit group. A person can be in more than one.
        </p>
        {error ? <Note tone="bad">{error}</Note> : null}
        {groups.length === 0 ? (
          <p className={cn(t.assessMeta, "m-0")}>No groups yet. Create one below and choose who is in it.</p>
        ) : (
          <ul className={card} aria-label="Trainee groups">
            {groups.map((group, index) => (
              <li key={group.id} className={cn(row, "gap-2", index === 0 && "border-t-0")}>
                <span className="flex-1">
                  {group.label}
                  <div className={t.assessMeta}>
                    {group.member_count} {group.member_count === 1 ? "person" : "people"}
                  </div>
                </span>
                {canManage ? (
                  <>
                    <button type="button" className={boardButtonSmall} onClick={() => setEditing(group)}>
                      People
                    </button>
                    <button type="button" className={boardButtonSmall} onClick={() => open({ kind: "rename", group })}>
                      Rename
                    </button>
                    <button type="button" className={boardButtonSmall} onClick={() => open({ kind: "delete", group })}>
                      Delete
                    </button>
                  </>
                ) : null}
              </li>
            ))}
          </ul>
        )}

        {canManage ? (
          <Fold title="Create a group">
            <div className={t.assessMeta}>Everyone in your organisation sees the same group names.</div>
            <input
              aria-label="New group name"
              value={groupLabel}
              onChange={(event) => setGroupLabel(event.target.value)}
              className={boardInput}
              placeholder="e.g. Tuesday rotation"
              autoComplete="off"
            />
            <button type="button" className={cn(boardBtn("primary", true), "self-start")} disabled={busy || groupLabel.trim() === ""} onClick={() => createGroup()}>
              {busy ? "Working…" : "Create group"}
            </button>
          </Fold>
        ) : null}
      </div>

      <GroupMembersDialog
        orgSlug={orgSlug}
        group={editing}
        trainees={trainees}
        onClose={() => setEditing(null)}
        onSaved={onChanged}
      />

      <RenameGroupDialog
        orgSlug={orgSlug}
        group={pending?.kind === "rename" ? pending.group : null}
        onClose={() => setPending(null)}
        onSaved={onChanged}
      />

      <DeleteGroupDialog
        orgSlug={orgSlug}
        group={pending?.kind === "delete" ? pending.group : null}
        onClose={() => setPending(null)}
        onDeleted={onChanged}
      />
    </div>
  );
}
