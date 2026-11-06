"use client";

import { useMemo, useState } from "react";
import { ButtonLink } from "@/foundation/ui";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { boardPad, boardTab, boardTabs, boardChip } from "@/foundation/ui/boardKit";
import { useSurface } from "@/capabilities";
import { reviewPath } from "@/domains/assess/results/candidateNeighbours";
import { SlotReview } from "@/domains/assess/SlotReview";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import { orderedSlots, stationLabel } from "@/domains/assess/sessions/support";
import { cardTitle } from "@/domains/assess/chrome";

/**
 * Marking, without leaving the room.
 *
 * The same editor `SlotReview` renders as its own page, mounted here against
 * whichever station on this circuit has already finished. A station's
 * machine marking does not exist until the consultation ends — the engine has
 * nothing to score mid-station — so this cannot be filled in *during* a
 * consultation the way the retiring runner's schema rubric could; what it
 * does do is let a supervisor mark station 1 while station 2 is already
 * running, instead of leaving the live view for a separate screen per
 * station. A rubric fillable independent of machine scoring, against the
 * station's `marking_layout`, is a further redesign and stays out of scope —
 * see `docs/BACKLOG.md`.
 */
export function LiveMarkingSidebar({ data, orgSlug }: { data: CircuitConsole; orgSlug: string }) {
  const finished = useMemo(
    () => orderedSlots(data).filter((slot) => slot.ended_at !== null && slot.attempt_id),
    [data],
  );
  const [selected, setSelected] = useState<string | null>(null);
  const { hrefFor } = useSurface();

  const first = finished[0];
  if (!first) return null;

  const activeId = selected ?? finished.find((slot) => !slot.marked)?.id ?? first.id;
  const active = finished.find((slot) => slot.id === activeId) ?? first;

  return (
    <div className={boardPad}>
      <h2 className={cardTitle}>Mark a finished station</h2>
      <div className={boardTabs} role="tablist" aria-label="Finished stations">
        {finished.map((slot) => (
          <button
            key={slot.id}
            type="button"
            role="tab"
            aria-selected={slot.id === active.id}
            onClick={() => setSelected(slot.id)}
            className={boardTab(slot.id === active.id)}
          >
            {stationLabel(slot)}
            {slot.marked ? null : <span className={`${boardChip("warn")} ml-2`}>Unmarked</span>}
          </button>
        ))}
      </div>
      <p className={assessMeta}>
        The full marking form for this station opens here, the same as Slot review.
      </p>
      <ButtonLink
        href={hrefFor(reviewPath(active.id, active.attempt_id, data.sitting.id))}
        themeType="b2b"
        variant="secondary"
        className="self-start"
      >
        Mark {stationLabel(active)}
      </ButtonLink>
      <details>
        <summary className="cursor-pointer text-assess-label font-medium text-osce-ink-900">Open the marking form here</summary>
        <div className="pt-3.5">
          <SlotReview orgSlug={orgSlug} slotId={active.id} attemptId={active.attempt_id ?? null} />
        </div>
      </details>
    </div>
  );
}
