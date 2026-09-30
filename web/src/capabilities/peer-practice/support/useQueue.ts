"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAsync, useEventStream } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { joinQueue, leaveQueue, listPracticeSessions, readPracticeSession, readQueueStatus, queueStreamPath, type QueueStatus } from "../api";

import { latestQueueStatus } from "./queueState";

export type QueuePhase = "idle" | "joining" | "waiting" | "matched";

/**
 * What pressing "Join now" came to. The caller decides the words; the retiring
 * context raised a different toast for each of these.
 */
export type JoinOutcome =
  | { kind: "joined" }
  | { kind: "busy" }
  | { kind: "already_queued" }
  | { kind: "existing_session"; sessionId: string }
  | { kind: "failed"; cause: unknown };
export interface Queue {
  phase: QueuePhase;
  expired: boolean;
  status: QueueStatus | null;
  matchedSessionId: string | null;
  live: boolean;
  error: Error | null;
  restoring: boolean;
  retry: () => void;
  join: (examCode: string) => Promise<JoinOutcome>;
  leave: () => Promise<void>;
  reset: () => void;
  /** Follow a queue place the server made for us, e.g. a requeue after a declined match. */
  adopt: (entryId: string) => void;
}

/** One SSE subscription; refresh and cross-tab changes re-read the saved entry. */
export function useQueue(orgId: string | null, options: {
  entryId: string | null;
  onEntryId: (entryId: string | null) => void;
}): Queue {
  const { entryId, onEntryId } = options;
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
  const join = useCallback(async (examCode: string): Promise<JoinOutcome> => {
    if (operation.current) return { kind: "busy" };
    operation.current = true;
    setJoining(true);
    setError(null);
    try {
      // A room already open for this exam wins over a second place in line.
      const sessions = await listPracticeSessions();
      // An unanswered match is not a room yet: the queue entry still offers it.
      const existing = sessions.items.find((item) => item.exam_code === examCode && item.status !== "ended" &&
        (item.status !== "pending_accept" || item.my_accepted));
      if (existing) {
        const current = await readPracticeSession(existing.id);
        if (current.status !== "ended") return { kind: "existing_session", sessionId: current.id };
      }
      const result = await joinQueue(examCode, orgId);
      const wasQueued = result.entry_id === entryId && result.status === "waiting";
      setEntry(result);
      onEntryId(result.entry_id);
      return wasQueued ? { kind: "already_queued" } : { kind: "joined" };
    } catch (cause) {
      if (hasCode(cause, "already_queued")) return { kind: "already_queued" };
      return { kind: "failed", cause };
    } finally { operation.current = false; setJoining(false); }
  }, [orgId, entryId, onEntryId]);
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
  const adopt = useCallback((adopted: string) => {
    setEntry(null);
    setError(null);
    onEntryId(adopted);
  }, [onEntryId]);
  return {
    phase: joining ? "joining" : matchedSessionId ? "matched" : status?.status === "waiting" ? "waiting" : "idle",
    expired: status?.status === "expired", status, matchedSessionId,
    live: stream.connected, error: error ?? restored.error ?? stream.error,
    restoring: Boolean(entryId && !base && restored.loading), retry: restored.reload,
    join, leave, reset, adopt,
  };
}
function asError(cause: unknown): Error {
  return cause instanceof Error ? cause : new Error(String(cause));
}
