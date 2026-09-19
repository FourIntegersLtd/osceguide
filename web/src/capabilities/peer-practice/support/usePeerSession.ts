"use client";

import { useCallback, useEffect, useState } from "react";
import { useAsync } from "@/foundation/hooks";
import { useMicPreflight, type RoomGrant } from "@/foundation/livekit";
import {
  endPracticeSession,
  practiceVoiceToken,
  readPracticeSession,
  type PracticeSession,
} from "@/capabilities/peer-practice/api";

export type SessionPhase = "loading" | "ready" | "live" | "ended";

export interface PeerSessionState {
  phase: SessionPhase;
  session: PracticeSession | null;
  loading: boolean;
  loadError: Error | null;
  reload: () => void;
  grant: RoomGrant | null;
  /** Seconds since the pair were put in the room. Zero until it starts. */
  elapsed: number;
  busy: boolean;
  error: Error | null;
  mic: ReturnType<typeof useMicPreflight>;
  connect: () => Promise<void>;
  end: (reason?: string | null) => Promise<void>;
  /** The room dropped out from under us rather than being hung up. */
  dropped: boolean;
  noteDisconnected: (unexpected: boolean) => void;
}

/**
 * One paired session, run.
 *
 * The retiring core component was 1,165 lines and held eleven pieces of state,
 * two polling loops, a visibility listener and a second copy of the phase
 * arithmetic inside a one-second interval. Almost all of it existed to work out
 * what phase the session was in from a single `preparation_started_at`
 * timestamp, because the server did not say.
 *
 * `platform-api` does say: a practice session is matched, then started, then
 * ended, and the clock it exposes is `started_at`. So the phase is read rather
 * than computed, the clock is elapsed time rather than an authoritative
 * countdown the browser has no right to run, and what is left is this.
 */
export function usePeerSession(sessionId: string): PeerSessionState {
  const loaded = useAsync((signal) => readPracticeSession(sessionId, signal), [sessionId]);
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [dropped, setDropped] = useState(false);
  const [ended, setEnded] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const session = loaded.data;
  const serverEnded = Boolean(session?.ended_at) || session?.status === "ended";
  const mic = useMicPreflight(Boolean(session) && !serverEnded);

  const phase: SessionPhase = loaded.loading && !session
    ? "loading"
    : ended || serverEnded
      ? "ended"
      : grant
        ? "live"
        : "ready";

  // Deadline arithmetic rather than a decrementing counter: a background tab
  // throttles timers to once a minute, and the old client's clock drifted
  // minutes off across a tab switch.
  const startedAtMs = session?.started_at ? new Date(session.started_at).getTime() : null;
  useEffect(() => {
    if (phase !== "live") return;
    const tick = () => {
      setElapsed(
        startedAtMs === null ? 0 : Math.max(0, Math.round((Date.now() - startedAtMs) / 1000)),
      );
    };
    tick();
    const id = window.setInterval(tick, 1000);
    const onVisible = () => {
      if (document.visibilityState === "visible") tick();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [phase, startedAtMs]);

  const connect = useCallback(async () => {
    setBusy(true);
    setError(null);
    setDropped(false);
    try {
      if (mic.status !== "ready") await mic.request();
      setGrant(await practiceVoiceToken(sessionId));
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setBusy(false);
    }
  }, [mic, sessionId]);

  const end = useCallback(
    async (reason: string | null = null) => {
      setBusy(true);
      setError(null);
      // The room goes first: leaving the token live while the server marks the
      // session ended is how the retiring client left people talking into a
      // session that had already finished.
      setGrant(null);
      setEnded(true);
      try {
        await endPracticeSession(sessionId, reason);
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(false);
        loaded.reload();
      }
    },
    [sessionId, loaded],
  );

  const noteDisconnected = useCallback((unexpected: boolean) => {
    setGrant(null);
    setDropped(unexpected);
  }, []);

  return {
    phase,
    session,
    loading: loaded.loading,
    loadError: loaded.error,
    reload: loaded.reload,
    grant,
    elapsed,
    busy,
    error,
    mic,
    connect,
    end,
    dropped,
    noteDisconnected,
  };
}
