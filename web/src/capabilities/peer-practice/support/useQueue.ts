"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAsync, useEventStream } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { joinQueue, leaveQueue, listPracticeSessions, readPracticeSession, readQueueStatus, queueStreamPath, type QueueStatus } from "../api";

import { latestQueueStatus } from "./queueState";

export type QueuePhase = "idle" | "joining" | "waiting" | "matched";
export interface Queue {
  phase: QueuePhase;
  expired: boolean;
  status: QueueStatus | null;
  matchedSessionId: string | null;
  live: boolean;
  error: Error | null;
  restoring: boolean;
  retry: () => void;
  join: (examCode: string) => Promise<void>;
  leave: () => Promise<void>;
  reset: () => void;
}

/** One SSE subscription; refresh and cross-tab changes re-read the saved entry. */
export function useQueue(orgId: string | null, options: {
  entryId: string | null;
  onEntryId: (entryId: string | null) => void;
  onExistingSession?: (sessionId: string) => void;
}): Queue {
  const { entryId, onEntryId, onExistingSession } = options;
  const [entry, setEntry] = useState<QueueStatus | null>(null);
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const operation = useRef(false);
  const restored = useAsync(async (signal) => ({
    entry: entryId ? await readQueueStatus(entryId, signal) : null,
  }), [entryId]);
  const base = latestQueueStatus(entryId, entry, restored.data?.entry);
  const stream = useEventStream<QueueStatus>(base?.status === "waiting" ? queueStreamPath(base.entry_id) : null);
  // useEventStream retains its last frame. Never use a frame from an older entry.
  const status = latestQueueStatus(entryId, base, stream.data);
  const matchedSessionId = status?.status === "matched" ? status.session_id ?? null : null;
  const reset = useCallback(() => {
    setEntry(null);
    setError(null);
    onEntryId(null);
  }, [onEntryId]);
  useEffect(() => {
    // Synchronise persisted storage after the server invalidates an entry.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (hasCode(restored.error, "queue_entry_not_found")) reset();
  }, [restored.error, reset]);
  const join = useCallback(async (examCode: string) => {
    if (operation.current) return;
    operation.current = true;
    setJoining(true);
    setError(null);
    try {
      const sessions = await listPracticeSessions();
      const existing = sessions.items.find((item) => item.exam_code === examCode && item.status !== "ended");
      if (existing && onExistingSession) {
        const current = await readPracticeSession(existing.id);
        if (current.status !== "ended") { onExistingSession(current.id); return; }
      }
      const result = await joinQueue(examCode, orgId);
      setEntry(result);
      onEntryId(result.entry_id);
    } catch (cause) { setError(asError(cause)); }
    finally { operation.current = false; setJoining(false); }
  }, [orgId, onEntryId, onExistingSession]);
  const leave = useCallback(async () => {
    if (!entryId || operation.current) return;
    operation.current = true;
    setError(null);
    try { await leaveQueue(entryId); reset(); }
    catch (cause) {
      // A match can win the cancellation race. Recover the room instead of
      // pretending cancellation succeeded and leaving the other person alone.
      if (hasCode(cause, "queue_entry_not_found")) {
        try {
          const latest = await readQueueStatus(entryId);
          if (latest.status === "matched") setEntry(latest);
          else reset();
        } catch (readError) {
          if (hasCode(readError, "queue_entry_not_found")) reset();
          else setError(asError(readError));
        }
      } else setError(asError(cause));
    } finally { operation.current = false; }
  }, [entryId, reset]);
  return {
    phase: joining ? "joining" : matchedSessionId ? "matched" : status?.status === "waiting" ? "waiting" : "idle",
    expired: status?.status === "expired", status, matchedSessionId,
    live: stream.connected, error: error ?? restored.error ?? stream.error,
    restoring: Boolean(entryId && !base && restored.loading), retry: restored.reload,
    join, leave, reset,
  };
}
function asError(cause: unknown): Error {
  return cause instanceof Error ? cause : new Error(String(cause));
}
