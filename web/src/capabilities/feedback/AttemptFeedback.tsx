"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { HiOutlineArrowPath } from "react-icons/hi2";
import { useAsync, useMeEvents } from "@/foundation/hooks";
import { readAttempt } from "@/capabilities/attempt-runner/api";
import { HiOutlineFaceFrown } from "react-icons/hi2";
import { AsyncBoundary, B2CEmptyState, cn, productTokens } from "@/foundation/ui";
import { RubricFeedback } from "@/capabilities/feedback/RubricFeedback";
import { SavedLiveCoverage } from "./SavedLiveCoverage";
import { isTerminal, readFeedback, scoredAtLabel } from "@/capabilities/feedback/api";
import type { MarkedResult, MarkingRubric } from "@/capabilities/feedback/rubric";

const { b2cCard, b2cIconEmptyMd, b2cPickerChipBase } = productTokens;

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
export function AttemptFeedback({ attemptId, showLiveCoverage = false }: { attemptId: string; showLiveCoverage?: boolean }) {
  const state = useAsync((signal) => readFeedback(attemptId, signal), [attemptId]);
  const feedback = state.data;
  const pending = feedback !== null && (feedback.results ?? []).length === 0;

  const [attemptStatus, setAttemptStatus] = useState<string | null>(null);

  // The worker publishes `attempt` on this user's own event stream when marking
  // finishes or fails; this re-reads the attempt's status on that event (and on
  // a `resync`) rather than polling for it.
  const reReadFor = useRef<string | null>(null);
  const reload = state.reload;
  const tick = useCallback(async () => {
    try {
      const attempt = await readAttempt(attemptId);
      setAttemptStatus(attempt.status);
      if (!isTerminal(attempt.status)) return;
      const key = `${attemptId}:${attempt.status}`;
      if (reReadFor.current === key) return;
      reReadFor.current = key;
      reload();
    } catch {
      // Transient network errors should not tear down the wait state.
    }
  }, [attemptId, reload]);
  useEffect(() => {
    if (pending) void tick();
  }, [pending, tick]);
  useMeEvents(
    pending ? ["attempt"] : null,
    useCallback(
      (event) => {
        if (event.name === "resync" || event.data.attempt_id === attemptId) void tick();
      },
      [attemptId, tick],
    ),
  );

  if (pending && attemptStatus === "failed") {
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

  return <AsyncBoundary state={state}>{(read) => <>
    <Markings rubric={read.rubric} results={read.results ?? []} />
    {showLiveCoverage && <SavedLiveCoverage attemptId={attemptId} />}
  </>}</AsyncBoundary>;
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
function Markings({ rubric, results }: { rubric: MarkingRubric | null; results: MarkedResult[] }) {
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
      {rubric ? (
        <RubricFeedback rubric={rubric} result={showing} />
      ) : (
        // Only an attempt marked before rubrics existed has none; its answers
        // cannot be read without one, so say so rather than guess at a shape.
        <B2CEmptyState
          icon={HiOutlineFaceFrown}
          title="No feedback recorded"
          description="This attempt was marked before its exam had a rubric."
        />
      )}
    </div>
  );
}
