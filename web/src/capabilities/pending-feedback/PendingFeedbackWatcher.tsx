"use client";

import { useCallback, useEffect, useRef } from "react";
import { readAttempt } from "@/capabilities/attempt-runner/api";
import { readResults } from "@/capabilities/feedback/api";
import { pendingOutcome } from "./outcome";
import type { PendingFeedbackJob } from "./PendingFeedbackContext";

const RECONCILE_MS = [10_000, 15_000, 20_000, 30_000, 45_000];

/**
 * Polls attempt status until a result exists.
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

  useEffect(() => {
    let attempts = 0;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const startedAt = Math.min(job.startedAt, Date.now());

    const schedule = () => {
      const delay = RECONCILE_MS[Math.min(attempts, RECONCILE_MS.length - 1)];
      timer = setTimeout(() => void reconcile(), delay);
    };

    const reconcile = async () => {
      if (cancelled || settledRef.current) return;
      let resultCount = 0;
      let attemptStatus: string | null = null;
      try {
        resultCount = (await readResults(job.attemptId)).length;
        if (resultCount === 0) attemptStatus = (await readAttempt(job.attemptId)).status;
      } catch {
        // a failed read is not an outcome; ask again
      }
      const outcome = pendingOutcome({
        resultCount,
        attemptStatus,
        elapsedMs: Date.now() - startedAt,
      });
      if (outcome === "ready") return markReady();
      if (outcome === "failed") return markFailed();
      if (outcome === "expired") return markExpired();
      attempts += 1;
      if (!cancelled) schedule();
    };

    void reconcile();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [job.attemptId, job.startedAt, markReady, markExpired, markFailed]);

  return null;
}
