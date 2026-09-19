"use client";

import { useCallback, useRef, useState } from "react";
import { useEventStream } from "@/foundation/hooks";
import {
  joinQueue,
  leaveQueue,
  queueStreamPath,
  type QueueStatus,
} from "@/capabilities/peer-practice/api";

export type QueuePhase = "idle" | "joining" | "waiting" | "matched";

export interface Queue {
  phase: QueuePhase;
  /** The latest the server pushed: position, how many are waiting, the session. */
  status: QueueStatus | null;
  /** Set the moment a partner is found. The session to walk into. */
  matchedSessionId: string | null;
  /** True while the stream is up; false means the fallback read is carrying it. */
  live: boolean;
  error: Error | null;
  join: (examCode: string) => Promise<void>;
  leave: () => Promise<void>;
  /** Forget a finished match without leaving a queue we are no longer in. */
  reset: () => void;
}

/**
 * Waiting to be paired, from one place.
 *
 * The retiring client spread this across a context, a modal, a floating
 * indicator and a polling hook that asked for the status every three seconds
 * from each of them. There is one stream now and one state machine reading it:
 * the backend pushes a `QueueStatus` each time the answer changes and closes
 * the stream as soon as it stops being `waiting`, so the match arrives when it
 * happens rather than up to three seconds later.
 *
 * `orgId` is the whole of what an institution's version needs. The hook itself
 * knows only that an audience exists.
 */
export function useQueue(orgId: string | null): Queue {
  const [localPhase, setPhase] = useState<QueuePhase>("idle");
  const [entry, setEntry] = useState<QueueStatus | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const entryIdRef = useRef<string | null>(null);

  const watching = localPhase === "waiting" && entry !== null;
  const stream = useEventStream<QueueStatus>(
    watching ? queueStreamPath(entry.entry_id) : null,
    { enabled: watching },
  );

  const status = stream.data ?? entry;
  const matchedSessionId = status?.session_id ?? null;

  // Matched is a fact about the answer rather than a state to be moved into:
  // the stream's frame already says so, and an effect copying it across would
  // render the waiting screen once more before the room appeared.
  const phase: QueuePhase =
    matchedSessionId && localPhase === "waiting" ? "matched" : localPhase;

  const join = useCallback(
    async (examCode: string) => {
      setPhase("joining");
      setError(null);
      try {
        const placed = await joinQueue(examCode, orgId);
        entryIdRef.current = placed.entry_id;
        setEntry(placed);
        // Joining twice returns the place already held, which may already
        // carry a session: going straight to "waiting" would hide the match.
        setPhase(placed.session_id ? "matched" : "waiting");
      } catch (cause) {
        setPhase("idle");
        setError(asError(cause));
      }
    },
    [orgId],
  );

  const leave = useCallback(async () => {
    const entryId = entryIdRef.current;
    entryIdRef.current = null;
    setEntry(null);
    setPhase("idle");
    setError(null);
    if (!entryId) return;
    try {
      await leaveQueue(entryId);
    } catch (cause) {
      // The place is gone from this browser either way; a failure to tell the
      // server is worth showing but must not strand the person in a queue
      // screen they have already left.
      setError(asError(cause));
    }
  }, []);

  const reset = useCallback(() => {
    entryIdRef.current = null;
    setEntry(null);
    setError(null);
    setPhase("idle");
  }, []);

  return {
    phase,
    status,
    matchedSessionId,
    live: stream.connected,
    error: error ?? stream.error,
    join,
    leave,
    reset,
  };
}

function asError(cause: unknown): Error {
  return cause instanceof Error ? cause : new Error(String(cause));
}
