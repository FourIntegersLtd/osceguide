"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useToastContext } from "@/foundation/ui";
import { PendingFeedbackWatcher } from "./PendingFeedbackWatcher";

const STORAGE_KEY = "pending_platform_feedback_jobs";
const SETTLED_KEY = "pending_platform_feedback_settled";
const JOB_MAX_AGE_MS = 20 * 60 * 1000;

export interface PendingFeedbackJob {
  key: string;
  attemptId: string;
  stationLabel: string;
  reviewHref: string;
  startedAt: number;
  notify: boolean;
}

export type RegisterPendingInput = Omit<PendingFeedbackJob, "startedAt" | "notify">;

export type PushNoticeInput = {
  tone: "success" | "error" | "info" | "warning";
  title: string;
  message: string;
  href?: string;
  hrefLabel?: string;
};

interface PendingFeedbackContextValue {
  register: (input: RegisterPendingInput) => void;
  release: (key: string) => void;
  resolve: (key: string) => void;
  pushNotice: (input: PushNoticeInput) => void;
}

const PendingFeedbackContext = createContext<PendingFeedbackContextValue | null>(null);

export function useOptionalPendingFeedback() {
  return useContext(PendingFeedbackContext);
}

export function usePendingFeedback() {
  const ctx = useContext(PendingFeedbackContext);
  if (!ctx) throw new Error("usePendingFeedback requires PendingFeedbackProvider");
  return ctx;
}

/** Mock station feedback deep link (relative to workspace base). */
export function feedbackReviewHref(setId: string, entryId: string, attemptId: string) {
  return `/mocks/${setId}/stations/${entryId}?action=review&tab=feedback&attempt=${attemptId}`;
}

function readStored(): PendingFeedbackJob[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as PendingFeedbackJob[];
    const now = Date.now();
    return parsed.filter((job) => job?.key && now - job.startedAt < JOB_MAX_AGE_MS);
  } catch {
    return [];
  }
}

function writeStored(jobs: PendingFeedbackJob[]) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
  } catch {
    // ignore
  }
}

function broadcastSettled(key: string) {
  try {
    window.localStorage.setItem(SETTLED_KEY, JSON.stringify({ key, at: Date.now() }));
  } catch {
    // ignore
  }
}

export function PendingFeedbackProvider({ children }: { children: ReactNode }) {
  const toast = useToastContext();
  const [jobs, setJobs] = useState<PendingFeedbackJob[]>([]);
  const jobsRef = useRef<PendingFeedbackJob[]>([]);
  const noticeIdsRef = useRef<Map<string, string>>(new Map());

  const commit = useCallback((next: PendingFeedbackJob[]) => {
    jobsRef.current = next;
    writeStored(next);
    setJobs(next);
  }, []);

  const forget = useCallback(
    (key: string) => {
      commit(jobsRef.current.filter((job) => job.key !== key));
      const noticeId = noticeIdsRef.current.get(key);
      if (noticeId) {
        noticeIdsRef.current.delete(key);
        toast.dismiss(noticeId);
      }
    },
    [commit, toast],
  );

  const pushNotice = useCallback(
    (input: PushNoticeInput) => {
      toast.show({
        tone: input.tone,
        title: input.title,
        message: input.message,
        persistent: input.tone !== "info",
        action: input.href
          ? { label: input.hrefLabel ?? "Open", href: input.href }
          : undefined,
      });
    },
    [toast],
  );

  const showReady = useCallback(
    (job: PendingFeedbackJob) => {
      const id = noticeIdsRef.current.get(job.key) ?? `feedback-ready-${job.key}`;
      noticeIdsRef.current.set(job.key, id);
      toast.show({
        id,
        tone: "success",
        title: "Your feedback is ready",
        message: `${job.stationLabel} has been marked and is waiting for you.`,
        persistent: true,
        action: { label: "Review feedback", href: job.reviewHref },
        onDismiss: () => {
          noticeIdsRef.current.delete(job.key);
          forget(job.key);
          broadcastSettled(job.key);
        },
      });
    },
    [toast, forget],
  );

  useEffect(() => {
    const restored = readStored().map((job) => ({ ...job, notify: true }));
    jobsRef.current = restored;
    setJobs(restored);
  }, []);

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === SETTLED_KEY && event.newValue) {
        try {
          const { key } = JSON.parse(event.newValue) as { key?: string };
          if (key) forget(key);
        } catch {
          // ignore
        }
      }
      if (event.key === STORAGE_KEY) {
        const stored = readStored();
        const known = new Set(jobsRef.current.map((job) => job.key));
        const added = stored.filter((job) => !known.has(job.key)).map((j) => ({ ...j, notify: true }));
        if (added.length) commit([...jobsRef.current, ...added]);
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [forget, commit]);

  const register = useCallback(
    (input: RegisterPendingInput) => {
      const stale = noticeIdsRef.current.get(input.key);
      if (stale) {
        noticeIdsRef.current.delete(input.key);
        toast.dismiss(stale);
      }
      commit([
        ...jobsRef.current.filter((job) => job.key !== input.key),
        { ...input, startedAt: Date.now(), notify: false },
      ]);
    },
    [commit, toast],
  );

  const release = useCallback(
    (key: string) => {
      // Leaving the station arms the toast. It does not fire yet: the watcher
      // shows it when a result actually exists, so walking away mid-marking
      // does not claim the feedback is ready.
      commit(
        jobsRef.current.map((job) => (job.key === key ? { ...job, notify: true } : job)),
      );
    },
    [commit],
  );

  const resolve = useCallback(
    (key: string) => {
      forget(key);
      broadcastSettled(key);
    },
    [forget],
  );

  const value = useMemo(
    () => ({ register, release, resolve, pushNotice }),
    [register, release, resolve, pushNotice],
  );

  const handleReady = useCallback(
    (key: string) => {
      const job = jobsRef.current.find((entry) => entry.key === key);
      commit(jobsRef.current.filter((entry) => entry.key !== key));
      if (job?.notify) showReady(job);
    },
    [commit, showReady],
  );

  const handleExpired = useCallback(
    (key: string) => {
      forget(key);
    },
    [forget],
  );

  return (
    <PendingFeedbackContext.Provider value={value}>
      {children}
      {jobs.map((job) => (
          <PendingFeedbackWatcher
            key={job.key}
            job={job}
            onReady={handleReady}
            onExpired={handleExpired}
          />
        ))}
    </PendingFeedbackContext.Provider>
  );
}
