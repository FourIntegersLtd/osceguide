"use client";

import { Button } from "@/foundation/ui";
import type { Cohort, TraineeGroup } from "@/domains/assess/roster/api";
import {
  ADD_TO_GROUP_LABEL,
  MOVE_TO_YEAR_GROUP_LABEL,
  NO_YEAR_GROUP_LABEL,
} from "@/domains/assess/roster/support";

/** "No year group" in the move-to-year-group select. */
const NO_GROUP = "__none__";

const SELECT_CLASS = "rounded-md border border-b2b-border bg-canvas px-2 py-1 text-osce-body";

/**
 * The bulk controls above the trainee table: select everyone loaded, and, once
 * anyone is ticked, act on the ticked rows. The panel owns the calls and the
 * revoke confirmation; this only reports the choice.
 *
 * A year group (cohort) is one per person, so moving replaces it. A group is a
 * list a person can be on with others, so adding keeps who is already in it.
 */
export function TraineeBulkBar({
  rowIds,
  selected,
  cohorts,
  groups,
  busy,
  onSelect,
  onResend,
  onMove,
  onAddToGroup,
  onRevoke,
}: {
  rowIds: string[];
  selected: Set<string>;
  cohorts: Cohort[];
  groups: TraineeGroup[];
  busy: boolean;
  onSelect: (next: Set<string>) => void;
  onResend: () => void;
  onMove: (cohortId: string | null) => void;
  onAddToGroup: (groupId: string) => void;
  onRevoke: () => void;
}) {
  const allPicked = rowIds.length > 0 && rowIds.every((id) => selected.has(id));
  return (
    <div className="flex flex-wrap items-center gap-3 text-osce-body text-b2b-headline">
      <label className="flex items-center gap-2 text-osce-meta font-medium">
        <input
          type="checkbox"
          checked={allPicked}
          disabled={busy}
          onChange={() => onSelect(allPicked ? new Set() : new Set(rowIds))}
        />
        Select all on this page
      </label>
      {selected.size > 0 ? (
        <>
          <span className="font-medium">{selected.size} selected</span>
          <Button themeType="b2b" variant="secondary" size="sm" disabled={busy} onClick={onResend}>
            Resend invitations
          </Button>
          <select
            aria-label="Move to year group"
            className={SELECT_CLASS}
            value=""
            disabled={busy}
            onChange={(event) => {
              const choice = event.target.value;
              if (choice) onMove(choice === NO_GROUP ? null : choice);
            }}
          >
            <option value="">{MOVE_TO_YEAR_GROUP_LABEL}</option>
            <option value={NO_GROUP}>{NO_YEAR_GROUP_LABEL}</option>
            {cohorts.map((cohort) => (
              <option key={cohort.id} value={cohort.id}>
                {cohort.name}
              </option>
            ))}
          </select>
          {groups.length > 0 ? (
            <select
              aria-label="Add to group"
              className={SELECT_CLASS}
              value=""
              disabled={busy}
              onChange={(event) => {
                if (event.target.value) onAddToGroup(event.target.value);
              }}
            >
              <option value="">{ADD_TO_GROUP_LABEL}</option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.label}
                </option>
              ))}
            </select>
          ) : null}
          <Button themeType="b2b" variant="secondary" size="sm" disabled={busy} onClick={onRevoke}>
            Revoke access
          </Button>
          <button type="button" className="underline" onClick={() => onSelect(new Set())}>
            Clear
          </button>
        </>
      ) : null}
    </div>
  );
}
