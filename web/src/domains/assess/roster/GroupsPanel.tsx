"use client";

import { useCallback, useState } from "react";
import { HiOutlineUserGroup } from "react-icons/hi2";
import { Alert, Button, b2bTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { PanelCard } from "@/domains/assess/team/chrome";
import type { Trainee } from "@/domains/assess/api";
import { addTraineeGroup, type Cohort, type TraineeGroup } from "@/domains/assess/roster/api";
import { CohortsPanel } from "@/domains/assess/roster/CohortsPanel";
import { GroupMembersDialog } from "@/domains/assess/roster/GroupMembersDialog";
import {
  DeleteGroupDialog,
  RenameGroupDialog,
} from "@/domains/assess/roster/GroupEditDialogs";

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
    <div className="space-y-6">
      {error ? <Alert tone="danger">{error}</Alert> : null}

      <CohortsPanel
        orgSlug={orgSlug}
        cohorts={cohorts}
        canManage={canManage}
        onChanged={onChanged}
      />

      <PanelCard
        title="Groups"
        subtitle="A list of people you put on a circuit — a rotation team, a resit group. Somebody can be in several."
        icon={<HiOutlineUserGroup className="h-5 w-5" aria-hidden />}
      >
        {groups.length === 0 ? (
          <p className="text-osce-body text-b2b-mid">
            No groups yet. Create one below and choose who is in it.
          </p>
        ) : (
          <ul className="space-y-2" aria-label="Trainee groups">
            {groups.map((group) => (
              <li
                key={group.id}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-b2b-border px-3 py-2"
              >
                <span className="min-w-0 truncate text-osce-body font-medium text-b2b-headline">
                  {group.label}
                </span>
                <span className="flex shrink-0 items-center gap-3">
                  <span className="text-osce-caption text-b2b-mid">
                    {group.member_count} {group.member_count === 1 ? "person" : "people"}
                  </span>
                  {canManage ? (
                    <span className="flex items-center gap-2">
                      <Button
                        themeType="b2b"
                        variant="secondary"
                        size="sm"
                        onClick={() => setEditing(group)}
                      >
                        People
                      </Button>
                      <Button
                        themeType="b2b"
                        variant="secondary"
                        size="sm"
                        onClick={() => open({ kind: "rename", group })}
                      >
                        Rename
                      </Button>
                      <Button
                        themeType="b2b"
                        variant="secondary"
                        size="sm"
                        onClick={() => open({ kind: "delete", group })}
                      >
                        Delete
                      </Button>
                    </span>
                  ) : null}
                </span>
              </li>
            ))}
          </ul>
        )}

        {canManage ? (
          <div className="mt-5 border-t border-b2b-border pt-4">
            <p className="text-osce-body font-semibold text-b2b-headline">Create a group</p>
            <p className="mt-0.5 text-osce-caption text-b2b-mid">
              Everyone in your organisation sees the same group names.
            </p>
            <div className="mt-2 flex flex-col gap-2 sm:flex-row">
              <input
                aria-label="New group name"
                value={groupLabel}
                onChange={(event) => setGroupLabel(event.target.value)}
                className={`${b2bTokens.b2bInputBase} min-w-0 flex-1`}
                placeholder="e.g. Tuesday rotation"
                autoComplete="off"
              />
              <Button
                themeType="b2b"
                variant="secondary"
                disabled={busy || groupLabel.trim() === ""}
                onClick={() => void createGroup()}
              >
                {busy ? "Working…" : "Create group"}
              </Button>
            </div>
          </div>
        ) : null}
      </PanelCard>

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
