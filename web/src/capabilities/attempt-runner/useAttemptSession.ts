"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { RoomEvent, type Room } from "livekit-client";
import { useEventStream } from "@/foundation/hooks/useEventStream";
import { publishToAgent, type RoomGrant } from "@/foundation/livekit";
import {
  abandonAttempt,
  attemptVoiceToken,
  voiceQueuePath,
  type VoiceQueueStanding,
} from "@/capabilities/attempt-runner/api";

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
 *
 * `queued` means every patient is busy: the candidate has a place in line and
 * is connected on their own once a seat is free.
 */
export type AttemptPhase =
  | "idle"
  | "reading"
  | "connecting"
  | "queued"
  | "live"
  | "ending"
  | "ended"
  | "failed";

export interface AttemptSession {
  phase: AttemptPhase;
  attempt: StartedAttemptRef | null;
  grant: RoomGrant | null;
  /** 1 for the front of the line. Set only while `queued`. */
  queuePosition: number | null;
  /**
   * The patient has joined the room. The consultation clock starts here, not
   * when the screen opens: waiting in line and connecting are not the
   * candidate's time.
   */
  patientJoined: boolean;
  error: Error | null;
  /** Begin the reading period. */
  begin: () => void;
  /** Skip the rest of the reading period and dispatch the patient. */
  startConsultation: () => Promise<void>;
  /** Hang up and let the transcript be scored. */
  end: () => Promise<void>;
  /** Give up before the consultation began. */
  abandon: () => Promise<void>;
  /** Stop waiting for a patient. The attempt stays, so starting again rejoins the line at the back. */
  leaveQueue: () => void;
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
  const [answeredPosition, setAnsweredPosition] = useState<number | null>(null);
  const [patientJoined, setPatientJoined] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const roomRef = useRef<Room | null>(null);
  const stopWatchingRoomRef = useRef<(() => void) | null>(null);
  const attemptRef = useRef<StartedAttemptRef | null>(null);
  const startingRef = useRef(false);
  const endingRef = useRef(false);
  const warned = useRef<Set<number>>(new Set());
  const handledStandingRef = useRef<VoiceQueueStanding | null>(null);
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
      const answer = await attemptVoiceToken(running.id);
      if ("ready" in answer) {
        // Every patient is busy. The stream below says when a seat is ours.
        setAnsweredPosition(answer.position);
        setPhase("queued");
        return;
      }
      setAnsweredPosition(null);
      setGrant(answer);
      setPhase("live");
    } catch (cause) {
      fail(cause);
    } finally {
      startingRef.current = false;
    }
  }, [fail]);

  // Pushed, never polled: the server re-reads the line when a seat frees up.
  const standing = useEventStream<VoiceQueueStanding>(
    phase === "queued" && attempt ? voiceQueuePath(attempt.id) : null,
  ).data;

  useEffect(() => {
    // The hook keeps its last payload across streams, so a `ready` already
    // acted on must not send the candidate straight back for another token.
    if (phase !== "queued" || !standing || standing === handledStandingRef.current) return;
    handledStandingRef.current = standing;
    if (standing.ready) void startConsultation();
  }, [phase, standing, startConsultation]);

  // The stream's latest place once it has one; until then, the token route's.
  const queuePosition =
    phase !== "queued" ? null : standing && !standing.ready ? standing.position : answeredPosition;

  const leaveQueue = useCallback(() => {
    // Nothing to tell the server: an unwatched place lapses on its own, and
    // stopping the stream is what stops watching it.
    setAnsweredPosition(null);
    setPhase("idle");
  }, []);

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
    setAnsweredPosition(null);
    setPatientJoined(false);
    setPhase("idle");
    setAttempt(null);
    attemptRef.current = null;
    endingRef.current = false;
  }, [attempt]);

  const attachRoom = useCallback((room: Room | null) => {
    roomRef.current = room;
    stopWatchingRoomRef.current?.();
    stopWatchingRoomRef.current = null;
    if (!room) return;
    // The patient is the worker's agent participant. It may already be in the
    // room by the time we are connected, so look once before listening.
    const noticePatient = () => {
      const participants = [...room.remoteParticipants.values()];
      if (participants.some((participant) => participant.isAgent)) setPatientJoined(true);
    };
    noticePatient();
    room.on(RoomEvent.ParticipantConnected, noticePatient);
    stopWatchingRoomRef.current = () => room.off(RoomEvent.ParticipantConnected, noticePatient);
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
    queuePosition,
    patientJoined,
    error,
    begin,
    startConsultation,
    end,
    abandon,
    leaveQueue,
    attachRoom,
    reportError: fail,
    warnTimeRemaining,
  };
}
