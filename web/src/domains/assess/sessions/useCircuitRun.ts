"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
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
  /*
   * The server closes this stream for good once the circuit ends — it sends
   * one last snapshot, then the connection goes away (`core/sse.py`'s
   * `Snapshot.final`). A browser reads a clean server-side close as an error
   * and reconnects on a backoff regardless of why it closed, so without this
   * an ended circuit left open in a background tab retries forever. The last
   * frame this hook ever saw is the only place "ended" can be read from, since
   * that is exactly the frame the stream will not be replacing.
   */
  const [ended, setEnded] = useState(false);
  const stream = useEventStream<CircuitConsole>(consoleStreamPath(orgSlug, circuitId), {
    enabled: !ended,
  });
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  const data = stream.data ?? initial.data;
  useEffect(() => {
    if (data?.circuit.ended_at != null) setEnded(true);
  }, [data]);
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
 * In exam mode, subscribe-only, and that is a guarantee rather than a UI
 * state: the token the backend mints carries no publish permission, so a
 * candidate cannot be prompted and the transcript stays a record of what they
 * said to the patient. A training-mode token may publish (`RoomGrant.can_publish`),
 * so a supervisor can demonstrate on camera.
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
