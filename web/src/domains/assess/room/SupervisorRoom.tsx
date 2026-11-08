"use client";

import { useEffect, useState } from "react";
import { Alert, Button } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { VoiceRoom } from "@/foundation/livekit";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import type { CircuitConsole } from "@/domains/assess/sessions/api";
import type { ObserverRoom } from "@/domains/assess/sessions/useCircuitRun";
import { setFloor, setParticipantMic } from "@/domains/assess/room/api";
import { RoomGrid } from "@/domains/assess/room/RoomGrid";

/**
 * The supervisor's side of a training circuit's room: joined by itself while the room is open, with
 * the floor switch and per-person microphones, and "Close the room" once the circuit has ended.
 */
export function SupervisorRoom({
  data,
  orgSlug,
  circuitId,
  observer,
  onClose,
}: {
  data: CircuitConsole;
  orgSlug: string;
  circuitId: string;
  observer: ObserverRoom;
  /** Closes the room and redraws the console: an ended circuit's stream is shut, so nothing else would. */
  onClose: () => Promise<void>;
}) {
  const circuit = data.circuit;
  const ended = circuit.ended_at !== null;
  const open = circuit.started_at !== null && !circuit.room_closed_at;
  const [left, setLeft] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  const { grant, joining, failure: joinFailure, join } = observer;
  useEffect(() => {
    if (open && !left && !grant && !joining && !joinFailure) void join();
  }, [open, left, grant, joining, joinFailure, join]);

  if (!open) return null;

  const run = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setFailure(null);
    try {
      await action();
    } catch (cause) {
      setFailure(errorMessage(cause instanceof Error ? cause : new Error(String(cause))));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-label="Room">
      {ended ? (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <p className={assessMeta}>The consultation has ended. The room stays open until you close it.</p>
          <Button themeType="b2b" variant="commit" isLoading={busy} onClick={() => void run(onClose)}>
            Close the room
          </Button>
        </div>
      ) : null}
      {joinFailure || failure ? <Alert tone="danger">{joinFailure ?? failure}</Alert> : null}
      {grant ? (
        <VoiceRoom grant={grant} audio={false} video={false} onDisconnected={() => observer.leave()}>
          <RoomGrid
            controls={{
              onLeave: () => {
                setLeft(true);
                observer.leave();
              },
              floor: {
                open: circuit.open_floor,
                busy,
                onToggle: () => void run(() => setFloor(orgSlug, circuitId, !circuit.open_floor)),
              },
              onMic: (identity, allowed) => void run(() => setParticipantMic(orgSlug, circuitId, identity, allowed)),
            }}
          />
        </VoiceRoom>
      ) : left ? (
        <Button themeType="b2b" variant="secondary" onClick={() => setLeft(false)}>
          Rejoin the room
        </Button>
      ) : (
        <p className={assessMeta}>Joining the room...</p>
      )}
    </section>
  );
}
