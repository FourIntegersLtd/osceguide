"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useAsync } from "@/foundation/hooks";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import type { RatingValue } from "@/capabilities/feedback/rubric";
import { readMySlotReview, saveReview } from "@/domains/assess/api";
import { readSlotReviews } from "@/domains/assess/results";
import { RatingInput } from "@/domains/assess/results/RatingInput";
import { fieldValuesFor, formDomains, initialRatings, type ReviewForm } from "@/domains/assess/results/reviewForm";
import { SchemeAccordion } from "@/domains/assess/room/SchemeAccordion";
import type { SchemeDomain } from "@/domains/assess/room/schemeDomains";
import { PeerMarksSummary } from "@/domains/assess/sessions/PeerMarksSummary";
import { peerItem } from "@/domains/assess/room/peerMarks";
import { createSaveQueue, type TickSave } from "@/domains/assess/room/liveTicks";

/**
 * Marking while the patient speaks.
 *
 * It writes the supervisor's own draft review through the same call the marking page makes
 * (`PUT .../slots/{slot}/reviews/mine`, status draft), a moment after each tick, so the page opens
 * with these marks already in and nothing is entered twice.
 */
export function LiveMarkPanel({
  orgSlug,
  circuitId,
  slotId,
  tick,
}: {
  orgSlug: string;
  circuitId: string;
  slotId: string;
  /** Changes whenever the console stream sends a frame; the peer marks are re-read on it. */
  tick: unknown;
}) {
  const state = useAsync(
    async (signal) => {
      const [reviews, mine] = await Promise.all([
        readSlotReviews(orgSlug, slotId, signal),
        readMySlotReview(orgSlug, slotId, signal),
      ]);
      return { form: (reviews.form ?? null) as ReviewForm | null, mine };
    },
    [orgSlug, slotId],
  );
  if (state.loading) return <p className={`${assessMeta} p-4`}>Loading the marking scheme...</p>;
  if (!state.data) return <p className={`${assessMeta} p-4`}>The marking scheme is not available for this station.</p>;
  return (
    <Ticks
      key={slotId}
      orgSlug={orgSlug}
      circuitId={circuitId}
      slotId={slotId}
      tick={tick}
      form={state.data.form}
      initial={state.data.mine?.field_values}
      released={state.data.mine?.status === "completed"}
    />
  );
}

function Ticks({
  orgSlug,
  circuitId,
  slotId,
  tick,
  form,
  initial,
  released,
}: {
  orgSlug: string;
  circuitId: string;
  slotId: string;
  tick: unknown;
  form: ReviewForm | null;
  initial: Record<string, unknown> | undefined;
  /** The supervisor's review is already released: a live tick must not turn it back into a draft. */
  released: boolean;
}) {
  const [ratings, setRatings] = useState<Record<string, RatingValue>>(() => initialRatings(form, initial));
  const [status, setStatus] = useState<TickSave>("idle");
  const latest = useRef(ratings);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // A live tick sends ratings only and asks the server to merge them: notes typed on the marking page survive.
  const queue = useMemo(
    () =>
      createSaveQueue(
        () => saveReview(orgSlug, slotId, { fieldValues: fieldValuesFor(latest.current), status: "draft", partial: true }),
        setStatus,
      ),
    [orgSlug, slotId],
  );

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  function rate(path: string, value: RatingValue) {
    latest.current = { ...latest.current, [path]: value };
    setRatings(latest.current);
    if (timer.current) clearTimeout(timer.current);
    queue.touch();
    timer.current = setTimeout(() => void queue.flush(), 350);
  }

  const fields = formDomains(form).flatMap((d) => d.fields);
  const domains: SchemeDomain[] = formDomains(form).map((d) => ({
    id: d.id,
    title: d.label,
    items: d.fields.map((f) => ({ key: f.path, label: f.competency_id ? f.label : d.label })),
  }));
  const labels: Record<string, string> = {};
  for (const f of fields) labels[peerItem(f.domain_id, f.competency_id ?? undefined)] = f.competency_id ? `${f.domain_label}: ${f.label}` : f.domain_label;

  if (released) return <p className={`${assessMeta} p-4`}>This review is already released, so it is not marked live. Reopen it on the marking page to change it.</p>;
  if (!form || domains.length === 0) return <p className={`${assessMeta} p-4`}>This station has nothing to rate live.</p>;
  return (
    <SchemeAccordion
      title="Marking"
      domains={domains}
      isDone={(path) => ratings[path] !== undefined}
      status={
        status === "failed" ? (
          <button type="button" onClick={() => { queue.touch(); void queue.flush(); }} className="text-assess-meta text-osce-danger underline underline-offset-2">
            Not saved. Retry
          </button>
        ) : (
          <span className={`${assessMeta} transition-opacity duration-150 motion-reduce:transition-none ${status === "idle" ? "opacity-0" : ""}`}>
            {status === "saving" ? "Saving..." : "Saved"}
          </span>
        )
      }
      renderItem={(item) => (
        <div className="flex items-center justify-between gap-3">
          <span className="min-w-0 flex-1">{item.label}</span>
          <RatingInput rating={form.rating} label={item.label} value={ratings[item.key] ?? null} onChange={(value) => rate(item.key, value)} />
        </div>
      )}
      footer={<PeerMarksSummary orgSlug={orgSlug} circuitId={circuitId} slotId={slotId} tick={tick} labels={labels} />}
    />
  );
}
