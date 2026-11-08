"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { LuMessageSquare } from "react-icons/lu";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { cn } from "@/foundation/ui/cn";
import { savePeerMarks, type Scheme } from "@/domains/assess/room/api";
import { createSaveQueue, type TickSave } from "@/domains/assess/room/liveTicks";
import { PEER_RATINGS, marksFor, stateFrom, withMark, type PeerState } from "@/domains/assess/room/peerMarks";
import { SchemeAccordion } from "@/domains/assess/room/SchemeAccordion";
import { domainsOf } from "@/domains/assess/room/schemeDomains";

/** A trainee watching someone else's turn marks the same scheme; each tick is saved for the supervisor. */
export function PeerScheme({ scheme, circuitId, slotId }: { scheme: Scheme; circuitId: string; slotId: string }) {
  const domains = domainsOf(scheme);
  const [marks, setMarks] = useState<PeerState>({});
  const [status, setStatus] = useState<TickSave>("idle");
  const [commenting, setCommenting] = useState<string | null>(null);
  const latest = useRef(marks);
  // Every item touched since this panel opened; saving one again is harmless, so nothing is lost to a race.
  const touched = useRef(new Set<string>());
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // What I marked before a reload (an empty save answers with my marks; refused when the turn is closed).
  useEffect(() => {
    let live = true;
    savePeerMarks(circuitId, slotId, [])
      .then((saved) => {
        if (!live) return;
        const mine = stateFrom(saved);
        latest.current = { ...mine, ...latest.current };
        setMarks(latest.current);
      })
      .catch(() => undefined);
    return () => { live = false; };
  }, [circuitId, slotId]);

  const queue = useMemo(
    () =>
      createSaveQueue(() => savePeerMarks(circuitId, slotId, marksFor(latest.current, [...touched.current])), setStatus),
    [circuitId, slotId],
  );

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  function change(item: string, patch: { rating?: string | null; comment?: string | null }) {
    latest.current = withMark(latest.current, item, patch);
    setMarks(latest.current);
    touched.current.add(item);
    queue.touch();
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => void queue.flush(), 350);
  }

  return (
    <SchemeAccordion
      title="Marking scheme"
      domains={domains}
      isDone={(key) => Boolean(marks[key]?.rating)}
      status={
        status === "failed" ? (
          <button type="button" onClick={() => { queue.touch(); void queue.flush(); }} className="text-assess-meta text-osce-danger underline underline-offset-2">
            Not saved. Retry
          </button>
        ) : (
          <span className={cn(assessMeta, "transition-opacity duration-150 motion-reduce:transition-none", status === "idle" && "opacity-0")}>
            {status === "saving" ? "Saving..." : "Saved"}
          </span>
        )
      }
      renderItem={(item) => (
        <div>
          <div className="flex items-center gap-2">
            <span className="min-w-0 flex-1 truncate" title={item.label}>{item.label}</span>
            <div role="group" aria-label={`Mark ${item.label}`} className="flex shrink-0 overflow-hidden rounded-md border border-osce-ink-200">
              {PEER_RATINGS.map((r) => (
                <button
                  key={r.value}
                  type="button"
                  aria-pressed={marks[item.key]?.rating === r.value}
                  aria-label={`${item.label}: ${r.label}`}
                  title={r.label}
                  onClick={() => change(item.key, { rating: r.value })}
                  className={cn(
                    "h-7 w-8 text-assess-meta font-medium transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-osce-accent motion-reduce:transition-none",
                    marks[item.key]?.rating === r.value ? "bg-osce-accent text-white" : "bg-white text-osce-ink-600 hover:bg-osce-ink-50",
                  )}
                >
                  {r.value}
                </button>
              ))}
            </div>
            <button
              type="button"
              aria-label={`Comment on ${item.label}`}
              aria-expanded={commenting === item.key}
              onClick={() => setCommenting(commenting === item.key ? null : item.key)}
              className={cn("grid h-7 w-7 shrink-0 place-items-center rounded-md hover:bg-osce-ink-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent", marks[item.key]?.comment ? "text-osce-accent" : "text-osce-ink-500")}
            >
              <LuMessageSquare aria-hidden className="h-4 w-4" />
            </button>
          </div>
          {commenting === item.key ? (
            <textarea
              aria-label={`Comment on ${item.label}`}
              rows={2}
              maxLength={2000}
              value={marks[item.key]?.comment ?? ""}
              onChange={(e) => change(item.key, { comment: e.target.value })}
              className="mt-1 w-full rounded-md border border-osce-ink-200 p-2 text-assess-desc"
            />
          ) : null}
        </div>
      )}
    />
  );
}
