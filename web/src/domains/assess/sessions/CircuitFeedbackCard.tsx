"use client";

import { useState } from "react";
import { HiCheckCircle } from "react-icons/hi2";
import { Alert, AsyncBoundary, Button, ButtonLink, b2bTokens, Panel } from "@/foundation/ui";
import type { AsyncState } from "@/foundation/hooks";
import {
  finalizeCircuitReview,
  type CircuitReviewState,
} from "@/domains/assess/sessions/api";
import type { CircuitConsole } from "@/domains/assess/sessions/api";

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
  current,
  ended,
  marked,
  total,
  busy,
  offline,
  publish,
}: {
  current: CircuitReviewState;
  ended: boolean;
  marked: number;
  total: number;
  busy: string | null;
  offline: boolean;
  publish: (notes: string | null) => Promise<boolean>;
}) {
  const [notes, setNotes] = useState(current.review?.merged_notes ?? "");
  const publishedAt = current.state === "published" ? current.review.finalized_at : null;

  return (
    <div>
    <Panel
      title="Share this circuit's feedback"
      description="Shares one summary of all the marking on this circuit. Candidates see it as their feedback. If you edit it and share again, the new version replaces the old one."
    >
      <div className="space-y-3">
      <p className="text-osce-caption font-medium text-b2b-headline">
        Marked on {marked} of {total} station{total === 1 ? "" : "s"}
      </p>

      <label htmlFor="circuit-feedback-notes" className="sr-only">
        Notes on the circuit as a whole
      </label>
      <textarea
        id="circuit-feedback-notes"
        value={notes}
        onChange={(event) => setNotes(event.target.value)}
        rows={3}
        placeholder="Anything to say about the circuit as a whole (optional)"
        className={`${b2bTokens.b2bInputBase} w-full`}
      />

      {publishedAt ? (
        <Alert tone="success">
          Published {new Date(publishedAt).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}.
          Publishing again replaces it.
        </Alert>
      ) : (
        <p className="text-osce-caption text-b2b-mid">Not published yet.</p>
      )}

      {marked === 0 ? (
        <p className="text-osce-caption text-b2b-mid">
          You can publish once at least one station is marked; this is the step that finalises the circuit&apos;s feedback.{" "}
          {ended ? (
            <ButtonLink href="#circuit-review" themeType="b2b" variant="ghost">
              Go to circuit feedback
            </ButtonLink>
          ) : null}
        </p>
      ) : null}

      <Button
        themeType="b2b"
        variant="secondary"
        isLoading={busy === "publish"}
        disabled={busy !== null || offline || marked === 0}
        onClick={() => publish(notes.trim() || null)}
      >
        <HiCheckCircle className="h-4 w-4 shrink-0 text-b2b-success-text" aria-hidden />
        {publishedAt ? "Publish again" : "Publish circuit feedback"}
      </Button>
      </div>
    </Panel>
    </div>
  );
}
