"use client";

import { useEffect, useState } from "react";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { byMarker, ratingWord } from "@/domains/assess/room/peerMarks";
import { readPeerMarksForStaff, type PeerMarks } from "@/domains/assess/room/api";

/** What the trainees watching this turn have marked, by marker, as they save it. */
export function PeerMarksSummary({
  orgSlug,
  circuitId,
  slotId,
  tick,
  labels,
}: {
  orgSlug: string;
  circuitId: string;
  slotId: string;
  tick: unknown;
  labels: Record<string, string>;
}) {
  const [marks, setMarks] = useState<PeerMarks | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    readPeerMarksForStaff(orgSlug, circuitId, slotId, controller.signal)
      .then(setMarks)
      .catch(() => undefined);
    return () => controller.abort();
  }, [orgSlug, circuitId, slotId, tick]);

  const groups = byMarker(marks, labels);
  return (
    <section aria-label="From the room" className="border-t border-osce-ink-100 px-4 py-3">
      <h3 className="m-0 mb-1 text-assess-desc font-medium text-osce-ink-900">From the room</h3>
      {groups.length === 0 ? (
        <p className={assessMeta}>Nothing from the other trainees yet.</p>
      ) : (
        groups.map((group) => (
          <details key={group.markerId} className="border-b border-osce-ink-100 last:border-b-0">
            <summary className="flex h-9 cursor-pointer list-none items-center justify-between text-assess-desc text-osce-ink-900 [&::-webkit-details-marker]:hidden">
              <span>{group.name}</span>
              <span className={assessMeta}>{group.rows.length} marked</span>
            </summary>
            <ul className="m-0 list-none pb-2 pl-0">
              {group.rows.map((row) => (
                <li key={row.item} className="py-0.5 text-assess-desc text-osce-ink-700">
                  {row.label}: {row.rating ? ratingWord(row.rating) : "No rating"}
                  {row.comment ? ` · ${row.comment}` : ""}
                </li>
              ))}
            </ul>
          </details>
        ))
      )}
    </section>
  );
}
