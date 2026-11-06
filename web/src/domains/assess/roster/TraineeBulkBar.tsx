"use client";

import { card, row } from "@/domains/assess/ui";
import { cn } from "@/foundation/ui";
import type { Cohort, TraineeGroup } from "@/domains/assess/roster/api";
import {
  ADD_TO_GROUP_LABEL,
  MOVE_TO_YEAR_GROUP_LABEL,
  NO_YEAR_GROUP_LABEL,
} from "@/domains/assess/roster/support";
import { boardBtn, boardButtonSmall } from "@/foundation/ui/boardKit";

/** "No year group" in the move-to-year-group select. */
const NO_GROUP = "__none__";

const SELECT_CLASS =
  "box-border min-h-11 w-full rounded-control border border-osce-border bg-osce-surface px-3 text-osce-body text-osce-ink-900";

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
    <div className={cn(card, selected.size > 0 && "border-assess-chip-info-bg")}>
      <div className={cn(row, "gap-2 border-t-0")}>
        <label className="m-0 flex min-h-8 items-start gap-2.5 text-assess-label font-normal">
          <input
            type="checkbox"
            className="mt-0.5 h-[18px] w-[18px] accent-osce-accent"
            checked={allPicked}
            disabled={busy}
            onChange={() => onSelect(allPicked ? new Set() : new Set(rowIds))}
          />
          Select all on this page
        </label>
        {selected.size > 0 ? (
          <>
            <b className="font-semibold">{selected.size} selected</b>
            <button type="button" className={boardButtonSmall} disabled={busy} onClick={onResend}>
              Resend invitations
            </button>
            <select
              aria-label="Move to year group"
              className={cn(SELECT_CLASS, "max-w-[200px]")}
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
                className={cn(SELECT_CLASS, "max-w-[180px]")}
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
            <button type="button" className={boardBtn("danger", true)} disabled={busy} onClick={onRevoke}>
              Revoke access
            </button>
            <button type="button" className="text-assess-label text-osce-accent hover:text-osce-accent-hover" onClick={() => onSelect(new Set())}>
              Clear
            </button>
          </>
        ) : null}
      </div>
    </div>
  );
}
