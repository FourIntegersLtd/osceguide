"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useAsync, useEventStream, useMeEvents } from "@/foundation/hooks";
import { useMicPreflight, type RoomGrant } from "@/foundation/livekit";
import { declinePracticeMatch, endPracticeSession, practiceSessionStreamPath, practiceVoiceToken, readPracticeSession, recordPracticePresence, type PracticeSession } from "../api";
import { formatCountdown } from "./examTimers";
import { latestSession, mapPhase, remainingSeconds } from "./sessionState";
export type { RunnerPhase } from "./sessionState";

export function usePeerSession(sessionId: string) {
  const loaded = useAsync((signal) => readPracticeSession(sessionId, signal), [sessionId]);
  const [mutation, setMutation] = useState<PracticeSession | null>(null);
  const [streamEnded, setStreamEnded] = useState(false);
  const terminal = streamEnded || ["completed", "ended"].includes(mapPhase(latestSession(sessionId, loaded.data, mutation)));
  const stream = useEventStream<PracticeSession>(practiceSessionStreamPath(sessionId), { enabled: !terminal });
  const session = latestSession(sessionId, loaded.data, stream.data, mutation);
  const runnerPhase = mapPhase(session);
  const ended = runnerPhase === "ended" || runnerPhase === "completed";
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [dropped, setDropped] = useState(false);
  const [endedByMe, setEndedByMe] = useState(false);
  const [now, setNow] = useState(Date.now);
  const mic = useMicPreflight(runnerPhase === "consultation" || runnerPhase === "debrief");
  if (ended && !streamEnded) setStreamEnded(true);
  // A queue match is not a room until both sides accept it; presence and end
  // are refused until then (`practice_session_not_accepted`).
  const pending = session?.status === "pending_accept";
  useEffect(() => {
    if (!session?.id || ended || pending) return;
    let live = true;
    void recordPracticePresence(sessionId).then((result) => { if (live) setMutation(result); })
      .catch((cause) => { if (live) setError(asError(cause)); });
    return () => { live = false; };
  }, [session?.id, sessionId, ended, pending]);
  // Both accepting, a decline, or the window expiring are all published as
  // `practice.session_updated` on this user's own event stream; a timeout at
  // the server's own deadline is the one clock still worth keeping, since the
  // read there is what actually times the window out.
  const reloadPending = loaded.reload;
  useMeEvents(
    pending ? ["practice.session_updated"] : null,
    useCallback(
      (event) => {
        if (event.name === "resync" || event.data.session_id === sessionId) reloadPending();
      },
      [sessionId, reloadPending],
    ),
  );
  useEffect(() => {
    if (!pending) return;
    const expiresAt = session?.accept_expires_at ? Date.parse(session.accept_expires_at) : Number.NaN;
    const expiry = Number.isFinite(expiresAt)
      ? window.setTimeout(loaded.reload, Math.max(0, expiresAt - Date.now()) + 250) : undefined;
    return () => window.clearTimeout(expiry);
  }, [pending, session?.accept_expires_at, loaded.reload]);
  useEffect(() => {
    if (ended) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [ended]);
  // Read at the server deadline (also drives APIs that advance phases on read).
  // No client phase transition; a failed read is surfaced with Retry.
  useEffect(() => {
    if (!session?.phase_ends_at || ended) return;
    const delay = Math.max(0, Date.parse(session.phase_ends_at) - Date.now()) + 250;
    const timer = window.setTimeout(loaded.reload, delay);
    return () => window.clearTimeout(timer);
  }, [session?.phase_ends_at, ended, loaded.reload]);
  const connect = useCallback(async () => {
    setBusy(true); setError(null); setDropped(false);
    try {
      if (mic.status !== "ready" && !await mic.request()) return;
      setMutation(await recordPracticePresence(sessionId));
      setGrant(await practiceVoiceToken(sessionId));
    } catch (cause) { setError(asError(cause)); }
    finally { setBusy(false); }
  }, [mic, sessionId]);
  const autoConnected = useRef(false);
  useEffect(() => {
    if (runnerPhase !== "consultation" && runnerPhase !== "debrief") return;
    if (autoConnected.current || !window.isSecureContext) return;
    autoConnected.current = true;
    void connect();
  }, [runnerPhase, connect]);
  const reloadSession = loaded.reload;
  const retry = useCallback(() => {
    setError(null);
    reloadSession();
    if (!ended && !pending) void recordPracticePresence(sessionId).then(setMutation).catch((cause) => setError(asError(cause)));
  }, [reloadSession, ended, pending, sessionId]);
  /** Ends the session; resolves to the failure, or null when it ended. */
  const end = useCallback(async (reason: string | null = null): Promise<Error | null> => {
    setBusy(true); setError(null);
    try {
      // Leaving before both have accepted is declining the match.
      const result = pending ? await declinePracticeMatch(sessionId) : await endPracticeSession(sessionId, reason);
      setEndedByMe(true); setMutation(result); setGrant(null);
      return null;
    } catch (cause) { const failure = asError(cause); setError(failure); return failure; }
    finally { setBusy(false); }
  }, [sessionId, pending]);
  const noteDisconnected = useCallback((unexpected: boolean) => { setGrant(null); setDropped(unexpected); }, []);
  const remaining = remainingSeconds(session?.phase_ends_at, now);
  return {
    runnerPhase, session, loading: loaded.loading, loadError: session ? null : loaded.error,
    reload: retry, grant: ended ? null : grant, busy, error: error ?? loaded.error ?? stream.error,
    mic, connect, end, endedByMe, dropped, noteDisconnected,
    remaining, phaseCountdown: remaining === null ? null : formatCountdown(remaining),
  };
}
function asError(cause: unknown): Error { return cause instanceof Error ? cause : new Error(String(cause)); }

export type PeerSessionState = ReturnType<typeof usePeerSession>;
