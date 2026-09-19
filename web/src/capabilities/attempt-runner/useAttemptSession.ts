"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Room } from "livekit-client";
import { publishToAgent, type RoomGrant } from "@/foundation/livekit";
import {
  abandonAttempt,
  attemptVoiceToken,
  createAttempt,
  type Attempt,
  type AttemptKind,
} from "@/capabilities/attempt-runner/api";

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
  attempt: Attempt | null;
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
  /** Tell the agent to wind down. Sent once, near the end. */
  warnTimeRemaining: (secondsLeft: number) => void;
}

export interface AttemptSessionInput {
  examCode: string;
  kind: AttemptKind;
  stationVersionId?: string | null;
  /** Skipped when zero, which is what a debrief and a peer session want. */
  readingSeconds: number;
  onEnded?: (attempt: Attempt) => void;
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
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const roomRef = useRef<Room | null>(null);
  const warned = useRef<Set<number>>(new Set());
  const inputRef = useRef(input);
  inputRef.current = input;

  const fail = useCallback((cause: unknown) => {
    setError(cause instanceof Error ? cause : new Error(String(cause)));
    setPhase("failed");
  }, []);

  const begin = useCallback(() => {
    setError(null);
    setPhase(inputRef.current.readingSeconds > 0 ? "reading" : "connecting");
  }, []);

  const startConsultation = useCallback(async () => {
    const { examCode, kind, stationVersionId } = inputRef.current;
    setPhase("connecting");
    setError(null);
    try {
      // The attempt is created first and frozen server-side; the worker then
      // fetches it by id. Nothing about the scenario travels through the
      // browser, so a tampered payload cannot change what is assessed.
      const created = await createAttempt({ examCode, kind, stationVersionId });
      setAttempt(created);
      setGrant(await attemptVoiceToken(created.id));
      setPhase("live");
    } catch (cause) {
      fail(cause);
    }
  }, [fail]);

  const end = useCallback(async () => {
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
    if (attempt) inputRef.current.onEnded?.(attempt);
  }, [attempt]);

  const abandon = useCallback(async () => {
    setGrant(null);
    try {
      if (attempt) await abandonAttempt(attempt.id);
    } catch {
      // An attempt that cannot be abandoned is left for the backend to expire;
      // blocking the candidate on it would be worse than a stale row.
    }
    setPhase("idle");
    setAttempt(null);
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
    warnTimeRemaining,
  };
}
