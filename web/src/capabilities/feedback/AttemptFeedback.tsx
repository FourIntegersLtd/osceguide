"use client";

import { useEffect, useRef, useState } from "react";
import { HiOutlineArrowPath } from "react-icons/hi2";
import { useAsync, useEventStream } from "@/foundation/hooks";
import { AsyncBoundary, cn, productTokens } from "@/foundation/ui";
import { FeedbackView } from "@/capabilities/feedback/FeedbackView";
import {
  attemptStreamPath,
  isTerminal,
  readResults,
  scoredAtLabel,
  type AssessmentResult,
} from "@/capabilities/feedback/api";

const { b2cCard, b2cIconEmptyMd, b2cPickerChipBase } = productTokens;

interface AttemptSnapshot {
  id: string;
  status: string;
}

/**
 * One attempt's feedback, including the wait for it.
 *
 * Marking is a background job of a minute or two, so "no result yet" is the
 * normal case rather than a failure. The retiring client met that with an SSE
 * hook, a reconciling poller and a ten-minute give-up timer; here the attempt
 * streams its own state until it is terminal and the result is re-read once.
 *
 * The same screen for a candidate and for an examiner: the API decides whose
 * results a person may read, and nothing in this component asks who is looking.
 */
export function AttemptFeedback({ attemptId }: { attemptId: string }) {
  const state = useAsync((signal) => readResults(attemptId, signal), [attemptId]);
  const results = state.data;
  const pending = results !== null && results.length === 0;

  const snapshot = useEventStream<AttemptSnapshot>(pending ? attemptStreamPath(attemptId) : null);

  // Once per arrival at a terminal state. `reload` changes `state`, which
  // would otherwise re-run this effect on the render it caused and ask again
  // for a result the job has not written yet — a loop on the one screen a
  // person sits and watches.
  const reReadFor = useRef<string | null>(null);
  const reload = state.reload;
  useEffect(() => {
    const status = snapshot.data?.status;
    if (!pending || !status || !isTerminal(status)) return;
    if (reReadFor.current === `${attemptId}:${status}`) return;
    reReadFor.current = `${attemptId}:${status}`;
    reload();
  }, [pending, snapshot.data, attemptId, reload]);

  if (pending && snapshot.data?.status === "failed") {
    // The attempt reached a terminal state with nothing scored. Saying so is
    // the whole point: the retiring client showed this as a spinner that never
    // stopped, and people sat in front of it.
    return (
      <div className={`${b2cCard} flex flex-col items-center justify-center gap-3 p-10 text-center`}>
        <p className="font-semibold text-b2c-text-secondary">This attempt could not be marked</p>
        <p className="text-osce-body text-b2c-text-muted">
          Something went wrong while scoring this consultation. The transcript is still available,
          and sitting the station again will produce a fresh mark.
        </p>
      </div>
    );
  }

  if (pending) {
    return (
      <div className={`${b2cCard} flex flex-col items-center justify-center gap-3 p-10 text-center`}>
        <HiOutlineArrowPath className={`animate-spin text-osce-accent ${b2cIconEmptyMd}`} />
        <p className="font-semibold text-b2c-text-secondary">Your feedback is being prepared</p>
        <p className="text-osce-body text-b2c-text-muted">
          Marking a consultation takes a minute or two. This page updates itself when it is ready.
        </p>
      </div>
    );
  }

  return <AsyncBoundary state={state}>{(items) => <Markings results={items} />}</AsyncBoundary>;
}

/**
 * The marking, with the older ones still reachable.
 *
 * Re-scoring under a new policy adds a result beside the old rather than
 * replacing it, so an attempt can have several. The newest is what a person
 * wants; the picker only appears when there is something else to pick, which
 * is the honest replacement for the retiring "Feedback History" tab — that
 * listed every feedback a station had ever produced, and a station's attempts
 * are the mock's list now.
 */
function Markings({ results }: { results: AssessmentResult[] }) {
  const latest = results.length - 1;
  const [selected, setSelected] = useState(latest);
  const showing = results[Math.min(selected, latest)];
  if (!showing) return null;

  return (
    <div className="space-y-4">
      {results.length > 1 && (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Markings of this attempt">
          {results.map((result, index) => (
            <button
              key={result.scored_at}
              type="button"
              onClick={() => setSelected(index)}
              aria-pressed={index === selected}
              className={cn(
                b2cPickerChipBase,
                "px-3 py-1.5 text-osce-meta",
                index === selected
                  ? "border-osce-accent bg-osce-accent-subtle text-osce-accent-hover"
                  : "border-b2c-border text-b2c-text-secondary",
              )}
            >
              {scoredAtLabel(result)}
              {index === latest ? " · latest" : ""}
            </button>
          ))}
        </div>
      )}
      <FeedbackView payload={showing.payload} />
    </div>
  );
}
