"use client";

import { useState } from "react";
import { Alert, AsyncBoundary, Button, ButtonLink } from "@/foundation/ui";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { boardInput } from "@/foundation/ui/boardKit";
import type { AsyncState } from "@/foundation/hooks";
import {
  finalizeCircuitReview,
  type CircuitReviewState,
} from "@/domains/assess/sessions/api";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import { RailSection } from "@/domains/assess/sessions/RailSection";
import Link from "next/link";
import { useSurface } from "@/capabilities";
import { useAssessWords } from "@/capabilities/assess-words";
import { reviewStations } from "@/domains/assess/sessions/circuitReviewSteps";
import { HIRE_MARK, hireFinishState, hireMarkRows } from "@/domains/assess/sessions/hireConsole";
import { slotReviewPath } from "@/domains/assess/sessions/support";

/**
 * Publishing what was marked, once the circuit is done.
 *
 * The retiring runner counted saved feedback by probing one request per slot;
 * the console frame already says which stations have been marked, so the count
 * is read rather than asked for. Publishing stays off until at least one has
 * been, which is the same rule the old card enforced.
 *
 * Whether it has already been published is read from the server
 * (`readCircuitReview`), so reopening the console after publishing says so,
 * with the notes that went out. It used to say only what it had done in this
 * visit, so a reopened console offered to publish again from empty notes.
 */
export function CircuitFeedbackCard({
  data,
  orgSlug,
  circuitId,
  review,
  busy,
  offline,
  run,
}: {
  data: CircuitConsole;
  orgSlug: string;
  circuitId: string;
  /** The circuit review read the runner holds, shared with the review step so both reload after a publish. */
  review: AsyncState<CircuitReviewState>;
  busy: string | null;
  /** The live stream is down, so the marks on screen may be stale. */
  offline: boolean;
  run: (name: string, action: () => Promise<unknown>) => Promise<void>;
}) {
  const slots = data.slots ?? [];
  // The marking and sharing steps are drawn once the circuit has ended, so that is the only place to go to.
  const ended = data.circuit.ended_at !== null;

  if (slots.length === 0) return null;

  return (
    <AsyncBoundary state={review}>
      {(current) => (
        <FeedbackForm
          key={current.review?.finalized_at ?? "none"}
          current={current}
          ended={ended}
          data={data}
          marked={slots.filter((slot) => slot.marked).length}
          total={slots.length}
          busy={busy}
          offline={offline}
          publish={async (notes) => {
            // `run` keeps a failure for the runner's banner rather than
            // throwing, so success is recorded from inside the action.
            let done = false;
            await run("publish", async () => {
              await finalizeCircuitReview(orgSlug, circuitId, notes);
              done = true;
            });
            if (done) review.reload();
            return done;
          }}
        />
      )}
    </AsyncBoundary>
  );
}

function FeedbackForm({
  data,
  current,
  ended,
  marked,
  total,
  busy,
  offline,
  publish,
}: {
  data: CircuitConsole;
  current: CircuitReviewState;
  ended: boolean;
  marked: number;
  total: number;
  busy: string | null;
  offline: boolean;
  publish: (notes: string | null) => Promise<boolean>;
}) {
  const w = useAssessWords();
  const { hrefFor } = useSurface();
  const stations = reviewStations(data);
  const finish = hireFinishState(stations);
  const [notes, setNotes] = useState(current.review?.merged_notes ?? "");
  const publishedAt = current.state === "published" ? current.review.finalized_at : null;

  const compact = !ended;

  return (
    <RailSection id="feedback" title={w.hiring && ended ? HIRE_MARK.title : "Send feedback to candidates"} hint={`${marked} of ${total} ${total === 1 ? "station" : "stations"} marked`} data-board="feedback">
      <p className="m-0 text-assess-label leading-normal text-osce-ink-500">
        {compact
          ? marked === 0
            ? "Mark at least one station first. Then you can send each candidate their feedback."
            : publishedAt
              ? "Feedback has been sent."
              : "Send each candidate their feedback once the stations are marked."
          : "Each candidate sees one summary of their marks. Sending again replaces the last one."}
      </p>

      {compact ? (
        <ButtonLink href="#circuit-review" themeType="b2b" variant="secondary" className="self-start">
          Send feedback
        </ButtonLink>
      ) : (
        <>
          <p className={assessMeta}>
            {marked} of {total} {total === 1 ? "station" : "stations"} marked
          </p>

          {w.hiring ? (
            <div role="table" aria-label="Your marks" className="flex flex-col text-assess-label">
              <div role="row" className="flex gap-2 font-semibold">
                {HIRE_MARK.headers.map((h) => (
                  <span key={h} role="columnheader" className="flex-1">{h}</span>
                ))}
              </div>
              {hireMarkRows(stations, data.slots ?? []).map((row) => (
                <div key={row.slotId} role="row" className="flex gap-2 py-1">
                  <span role="cell" className="flex-1">{row.label}</span>
                  <span role="cell" className="flex-1">{row.ai}</span>
                  <span role="cell" className="flex-1">
                    {row.yours === "Done" ? (
                      row.yours
                    ) : (
                      <Link href={hrefFor(slotReviewPath(row))} className="text-osce-accent underline">
                        {row.yours}
                      </Link>
                    )}
                  </span>
                </div>
              ))}
            </div>
          ) : null}

          <label htmlFor="circuit-feedback-notes" className="sr-only">
            Note for candidates
          </label>
          <textarea
            id="circuit-feedback-notes"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={4}
            placeholder="Add a note for everyone (optional)"
            className={`${boardInput} min-h-24 py-2.5`}
          />

          {publishedAt ? (
            <Alert tone="success">
              Sent {new Date(publishedAt).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}.
              Sending again replaces it.
            </Alert>
          ) : (
            <Alert tone="info">Not sent yet.</Alert>
          )}

          {marked === 0 ? (
            <p className={assessMeta}>
              Mark at least one station first. Then you can send each candidate their feedback.
            </p>
          ) : null}

          <Button
            themeType="b2b"
            variant="primary"
            className="self-start"
            isLoading={busy === "publish"}
            disabled={busy !== null || offline || marked === 0 || (w.hiring && finish.disabled)}
            onClick={() => publish(notes.trim() || null)}
          >
            {w.hiring ? HIRE_MARK.finish : publishedAt ? "Send again" : "Send feedback"}
          </Button>
          {w.hiring && finish.reason ? <p className={assessMeta}>{finish.reason}</p> : null}
        </>
      )}
    </RailSection>
  );
}
