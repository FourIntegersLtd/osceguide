"use client";

import { Button } from "@/foundation/ui";
import type { Cohort } from "@/domains/assess/roster/api";

/** "No group" in the move-to-group select. */
const NO_GROUP = "__none__";

/**
 * The bulk controls above the trainee table: select everyone loaded, and, once
 * anyone is ticked, act on the ticked rows. The panel owns the calls and the
 * revoke confirmation; this only reports the choice.
 */
export function TraineeBulkBar({
  rowIds,
  selected,
  cohorts,
  busy,
  onSelect,
  onResend,
  onMove,
  onRevoke,
}: {
  rowIds: string[];
  selected: Set<string>;
  cohorts: Cohort[];
  busy: boolean;
  onSelect: (next: Set<string>) => void;
  onResend: () => void;
  onMove: (cohortId: string | null) => void;
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
            aria-label="Move to group"
            className="rounded-md border border-b2b-border bg-canvas px-2 py-1 text-osce-body"
            value=""
            disabled={busy}
            onChange={(event) => {
              const choice = event.target.value;
              if (choice) onMove(choice === NO_GROUP ? null : choice);
            }}
          >
            <option value="">Move to group…</option>
            <option value={NO_GROUP}>No group</option>
            {cohorts.map((cohort) => (
              <option key={cohort.id} value={cohort.id}>
                {cohort.name}
              </option>
            ))}
          </select>
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
