"use client";

import { useCallback, useMemo, useState } from "react";
import { errorMessage, useAsync, useEventStream, type AsyncState } from "@/foundation/hooks";
import type { RoomGrant } from "@/foundation/livekit";
import {
  consoleStreamPath,
  observerToken,
  readConsole,
  type CircuitConsole,
  type ConsoleSlot,
} from "@/domains/assess/sessions/api";
import { orderedSlots } from "@/domains/assess/sessions/support";

export interface CircuitRun {
  /** The frame the screen draws: the stream's if it is up, the fetch's until then. */
  data: CircuitConsole | null;
  /** For the boundary — the first load is the only one that blocks the screen. */
  initial: AsyncState<CircuitConsole>;
  connected: boolean;
  slots: ConsoleSlot[];
  activeSlot: ConsoleSlot | null;
  /** The name of the control being awaited, or null. */
  busy: string | null;
  failure: string | null;
  run: (name: string, action: () => Promise<unknown>) => Promise<void>;
  dismissFailure: () => void;
}

/**
 * One circuit, one hook.
 *
 * The retiring runner spread this across `useSupervisorCircuitRunner` and
 * `useSupervisorSlotActions` — some sixty fields handed down through two
 * layouts — and it kept the examination's clock in the supervisor's browser,
 * broadcasting it to everyone else over LiveKit data packets. Whoever opened
 * the page last could silently restart a station, and a refresh lost the
 * timing altogether.
 *
 * Here the circuit runs itself on the server and this hook only watches it:
 * the console stream pushes every phase change, every clock, every alert. A
 * control is a request, and the next frame is the answer. Two supervisors with
 * the page open see one examination.
 */
export function useCircuitRun(orgSlug: string, circuitId: string): CircuitRun {
  const initial = useAsync(
    (signal) => readConsole(orgSlug, circuitId, signal),
    [orgSlug, circuitId],
  );
  const stream = useEventStream<CircuitConsole>(consoleStreamPath(orgSlug, circuitId));
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  const data = stream.data ?? initial.data;
  const slots = useMemo(() => (data ? orderedSlots(data) : []), [data]);
  const activeSlot = useMemo(
    () => slots.find((slot) => slot.id === data?.circuit.active_slot_id) ?? null,
    [slots, data],
  );

  const reload = initial.reload;
  const run = useCallback(
    async (name: string, action: () => Promise<unknown>) => {
      setBusy(name);
      setFailure(null);
      try {
        await action();
        // The stream will push the new state within the moment; reloading is
        // what makes the screen right if it happens to be down.
        reload();
      } catch (cause) {
        setFailure(errorMessage(cause instanceof Error ? cause : new Error(String(cause))));
      } finally {
        setBusy(null);
      }
    },
    [reload],
  );

  return {
    data,
    initial,
    connected: stream.connected,
    slots,
    activeSlot,
    busy,
    failure,
    run,
    dismissFailure: useCallback(() => setFailure(null), []),
  };
}

export interface ObserverRoom {
  grant: RoomGrant | null;
  joining: boolean;
  failure: string | null;
  join: () => Promise<void>;
  leave: () => void;
}

/**
 * The examiner's way into the room.
 *
 * Subscribe-only, and that is a guarantee rather than a UI state: the token
 * the backend mints carries no publish permission at all, so a candidate
 * cannot be prompted and the transcript stays a record of what they said to
 * the patient. The retiring runner gave the supervisor a microphone and a
 * camera in this room; see `docs/port-gaps.md`.
 */
export function useObserverRoom(orgSlug: string, circuitId: string): ObserverRoom {
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [joining, setJoining] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const join = useCallback(async () => {
    setJoining(true);
    setFailure(null);
    try {
      setGrant(await observerToken(orgSlug, circuitId));
    } catch (cause) {
      setFailure(errorMessage(cause instanceof Error ? cause : new Error(String(cause))));
    } finally {
      setJoining(false);
    }
  }, [orgSlug, circuitId]);

  return { grant, joining, failure, join, leave: useCallback(() => setGrant(null), []) };
}
