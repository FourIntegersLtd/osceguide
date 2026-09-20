"use client";

import { useCallback, useEffect, useRef } from "react";
import { readAttempt } from "@/capabilities/attempt-runner/api";
import { readResults, isTerminal } from "@/capabilities/feedback/api";
import type { PendingFeedbackJob } from "./PendingFeedbackContext";

const RECONCILE_MS = [10_000, 15_000, 20_000, 30_000, 45_000];
const MAX_WAIT_MS = 10 * 60 * 1000;

/**
 * Polls attempt status until a result exists — platform-api has no legacy SSE
 * yet; see `docs/port-gaps.md` (B6).
 */
export function PendingFeedbackWatcher({
  job,
  onReady,
  onExpired,
}: {
  job: PendingFeedbackJob;
  onReady: (key: string) => void;
  onExpired: (key: string) => void;
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
      try {
        const results = await readResults(job.attemptId);
        if (results.length > 0) {
          markReady();
          return;
        }
        const attempt = await readAttempt(job.attemptId);
        if (isTerminal(attempt.status) && attempt.status === "failed") {
          markExpired();
          return;
        }
      } catch {
        // retry
      }

      attempts += 1;
      if (Date.now() - startedAt >= MAX_WAIT_MS) {
        markExpired();
        return;
      }
      if (!cancelled) schedule();
    };

    void reconcile();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [job.attemptId, job.startedAt, markReady, markExpired]);

  return null;
}
