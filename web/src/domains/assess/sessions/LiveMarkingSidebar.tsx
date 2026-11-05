"use client";

import { useMemo, useState } from "react";
import { Badge, ButtonLink, FoldSection } from "@/foundation/ui";
import { useSurface } from "@/capabilities";
import { reviewPath } from "@/domains/assess/results/candidateNeighbours";
import { SlotReview } from "@/domains/assess/SlotReview";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import { orderedSlots, stationLabel } from "@/domains/assess/sessions/support";

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

  const activeId = selected ?? finished.find((slot) => !slot.has_review)?.id ?? first.id;
  const active = finished.find((slot) => slot.id === activeId) ?? first;

  return (
    <FoldSection title="Mark a finished station">
      <div className="mb-3 flex flex-wrap gap-2" role="tablist" aria-label="Finished stations">
        {finished.map((slot) => (
          <button
            key={slot.id}
            type="button"
            role="tab"
            aria-selected={slot.id === active.id}
            onClick={() => setSelected(slot.id)}
            className={`inline-flex items-center gap-1.5 rounded-control border px-3 py-1.5 text-osce-caption font-medium transition-colors ${
              slot.id === active.id
                ? "border-b2b-accent bg-b2b-accent text-white"
                : "border-b2b-border bg-b2b-surface text-b2b-mid hover:text-b2b-headline"
            }`}
          >
            {stationLabel(slot)}
            {slot.has_review ? null : (
              <Badge
                variant={slot.id === active.id ? "neutral" : "warning"}
                size="xs"
                className={slot.id === active.id ? "bg-white/20 text-white" : undefined}
              >
                Unmarked
              </Badge>
            )}
          </button>
        ))}
      </div>
      <p className="mb-3 text-osce-body text-b2b-mid">
        The full marking form for this station opens here, the same as Slot review.{" "}
        <ButtonLink
          href={hrefFor(reviewPath(active.id, active.attempt_id, data.sitting.id))}
          themeType="b2b"
          variant="ghost"
        >
          Mark {stationLabel(active)}
        </ButtonLink>
      </p>
      <SlotReview orgSlug={orgSlug} slotId={active.id} attemptId={active.attempt_id ?? null} />
    </FoldSection>
  );
}
