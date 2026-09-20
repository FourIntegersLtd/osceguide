"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Room } from "livekit-client";
import { publishToAgent, type RoomGrant } from "@/foundation/livekit";
import { abandonAttempt, attemptVoiceToken } from "@/capabilities/attempt-runner/api";

/** The minimum the runner needs back from whatever created the attempt. */
export interface StartedAttemptRef {
  id: string;
}

/**
 * Where a candidate is in one attempt.
 *
 * `reading` exists as a phase because the brief is part of the exam, not a
 * loading screen: the clock for it is separate and the patient must not be
 * dispatched until it ends.
 */
export type AttemptPhase = "idle" | "reading" | "connecting" | "live" | "ending" | "ended" | "failed";

export interface AttemptSession {
  phase: AttemptPhase;
  attempt: StartedAttemptRef | null;
  grant: RoomGrant | null;
  error: Error | null;
  /** Begin the reading period. */
  begin: () => void;
  /** Skip the rest of the reading period and dispatch the patient. */
  startConsultation: () => Promise<void>;
  /** Hang up and let the transcript be scored. */
  end: () => Promise<void>;
  /** Give up before the consultation began. */
  abandon: () => Promise<void>;
  attachRoom: (room: Room | null) => void;
  reportError: (cause: unknown) => void;
  /** Tell the agent to wind down. Sent once, near the end. */
  warnTimeRemaining: (secondsLeft: number) => void;
}

export interface AttemptSessionInput {
  /**
   * How this arm creates the attempt it is entitled to run.
   *
   * Train posts to `/attempts` for free practice or to its station set's entry;
   * Assess starts a circuit slot. The runner must not know which, or it would
   * need a branch per arm and stop being a capability — so the caller supplies
   * the one call that differs and everything after it is shared.
   *
   * Optional when `attemptId` is given: the consumer station screen creates
   * the attempt as soon as the station is opened, because the brief it reads
   * during the reading period *is* the attempt's, and then there is nothing
   * left to create when the patient is called.
   */
  start?: () => Promise<StartedAttemptRef>;
  /**
   * An attempt that already exists, to run rather than create.
   *
   * A reload during a station must not burn a second attempt against the
   * exam's limit — the backend counts one at creation — so the screen keeps
   * the id and hands it back here.
   */
  attemptId?: string | null;
  /** Skipped when zero, which is what a debrief and a peer session want. */
  readingSeconds: number;
  onEnded?: (attemptId: string) => void;
}

/**
 * One attempt, from "start" to "scored".
 *
 * All three arms drive this: Train starts one from a mock, Assess starts one
 * from a circuit slot, Hire from an exam-mode sitting. They differ in what
 * they pass in, not in what happens next, which is the whole reason the runner
 * is a capability and not three implementations.
 */
export function useAttemptSession(input: AttemptSessionInput): AttemptSession {
  const [phase, setPhase] = useState<AttemptPhase>("idle");
  const [attempt, setAttempt] = useState<StartedAttemptRef | null>(null);
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const roomRef = useRef<Room | null>(null);
  const attemptRef = useRef<StartedAttemptRef | null>(null);
  const startingRef = useRef(false);
  const endingRef = useRef(false);
  const warned = useRef<Set<number>>(new Set());
  const inputRef = useRef(input);
  inputRef.current = input;

  const fail = useCallback((cause: unknown) => {
    setGrant(null);
    setError(cause instanceof Error ? cause : new Error(String(cause)));
    setPhase("failed");
  }, []);

  const begin = useCallback(() => {
    setError(null);
    setPhase(inputRef.current.readingSeconds > 0 ? "reading" : "connecting");
  }, []);

  const startConsultation = useCallback(async () => {
    if (startingRef.current || endingRef.current) return;
    startingRef.current = true;
    setPhase("connecting");
    setError(null);
    try {
      /*
       * The attempt is frozen server-side and the worker fetches it by id.
       * Nothing about the scenario travels through the browser, so a tampered
       * payload cannot change what is assessed.
       *
       * It may already exist — the consumer screen creates it when the station
       * opens, so the reading period has a brief to show — in which case this
       * mints a token for it rather than creating a second one.
       */
      const { attemptId, start } = inputRef.current;
      const running = attemptId ? { id: attemptId } : attemptRef.current ?? await start?.();
      if (!running) throw new Error("This station has no attempt to run.");
      attemptRef.current = running;
      setAttempt(running);
      setGrant(await attemptVoiceToken(running.id));
      setPhase("live");
    } catch (cause) {
      fail(cause);
    } finally {
      startingRef.current = false;
    }
  }, [fail]);

  const end = useCallback(async () => {
    if (endingRef.current) return;
    endingRef.current = true;
    setPhase("ending");
    // Clearing the grant is what disconnects: LiveKitRoom reconnects on the
    // next render while it still has credentials.
    setGrant(null);
    const room = roomRef.current;
    try {
      if (room && room.state !== "disconnected") await room.disconnect();
    } catch {
      // Already gone. The server ends the session from its side regardless.
    }
    setPhase("ended");
    if (attempt) inputRef.current.onEnded?.(attempt.id);
  }, [attempt]);

  const abandon = useCallback(async () => {
    setGrant(null);
    const id = attempt?.id ?? inputRef.current.attemptId ?? null;
    try {
      if (id) await abandonAttempt(id);
    } catch {
      // An attempt that cannot be abandoned is left for the backend to expire;
      // blocking the candidate on it would be worse than a stale row.
    }
    setPhase("idle");
    setAttempt(null);
    attemptRef.current = null;
    endingRef.current = false;
  }, [attempt]);

  const attachRoom = useCallback((room: Room | null) => {
    roomRef.current = room;
  }, []);

  const warnTimeRemaining = useCallback((secondsLeft: number) => {
    // Once per threshold: the clock ticks every second and the agent does not
    // need sixty copies of "one minute left".
    if (warned.current.has(secondsLeft)) return;
    warned.current.add(secondsLeft);
    void publishToAgent(roomRef.current, "time_warning", { secondsLeft });
  }, []);

  useEffect(() => {
    return () => {
      // Leaving the page mid-consultation must not leave a room open holding a
      // worker; the attempt is still scored from whatever was transcribed.
      const room = roomRef.current;
      if (room && room.state !== "disconnected") void room.disconnect();
    };
  }, []);

  return {
    phase,
    attempt,
    grant,
    error,
    begin,
    startConsultation,
    end,
    abandon,
    attachRoom,
    reportError: fail,
    warnTimeRemaining,
  };
}
