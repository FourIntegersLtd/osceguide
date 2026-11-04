"use client";

import { useCallback, useEffect, useRef } from "react";
import { readAttempt } from "@/capabilities/attempt-runner/api";
import { readResults } from "@/capabilities/feedback/api";
import { useMeEvents } from "@/foundation/hooks";
import { MAX_WAIT_MS, pendingOutcome } from "./outcome";
import type { PendingFeedbackJob } from "./PendingFeedbackContext";

/**
 * Waits for a result to exist. Reads once on mount and again whenever `/me/events` says the attempt
 * changed (the scorer publishes `attempt` when it stores a result or gives up) or the stream
 * reconnected (`resync`). Nothing polls: a timer only flips the copy to "taking longer".
 */
export function PendingFeedbackWatcher({
  job,
  onReady,
  onExpired,
  onFailed,
}: {
  job: PendingFeedbackJob;
  onReady: (key: string) => void;
  onExpired: (key: string) => void;
  onFailed: (key: string) => void;
}) {
  const settledRef = useRef(false);

  const markReady = useCallback(() => {
    if (settledRef.current) return;
    settledRef.current = true;
    onReady(job.key);
  }, [job.key, onReady]);

  const markExpired = useCallback(() => {
    if (settledRef.current) return;
    settledRef.current = true;
    onExpired(job.key);
  }, [job.key, onExpired]);

  const markFailed = useCallback(() => {
    if (settledRef.current) return;
    settledRef.current = true;
    onFailed(job.key);
  }, [job.key, onFailed]);

  const reconcile = useCallback(async () => {
    if (settledRef.current) return;
    let resultCount = 0;
    let attemptStatus: string | null = null;
    try {
      resultCount = (await readResults(job.attemptId)).length;
      if (resultCount === 0) attemptStatus = (await readAttempt(job.attemptId)).status;
    } catch {
      // a failed read is not an outcome; the next event asks again
    }
    const outcome = pendingOutcome({ resultCount, attemptStatus, elapsedMs: 0 });
    if (outcome === "ready") markReady();
    else if (outcome === "failed") markFailed();
  }, [job.attemptId, markReady, markFailed]);

  useEffect(() => {
    void reconcile();
  }, [reconcile]);

  useMeEvents(["attempt"], (event) => {
    if (event.name === "resync" || event.data.attempt_id === job.attemptId) void reconcile();
  });

  // Display only: after MAX_WAIT_MS the banner says it is taking longer. No read happens here.
  useEffect(() => {
    const remaining = Math.max(0, MAX_WAIT_MS - (Date.now() - Math.min(job.startedAt, Date.now())));
    const timer = setTimeout(markExpired, remaining);
    return () => clearTimeout(timer);
  }, [job.startedAt, markExpired]);

  return null;
}
